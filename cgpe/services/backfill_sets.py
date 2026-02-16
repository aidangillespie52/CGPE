# cgpe/services/backfill_sets.py

import aiohttp

from cgpe.pipeline.set import run_set_pipeline
from cgpe.pipeline.detail import run_detail_pipeline
from cgpe.logging.logger import setup_logger
from cgpe.storage.detail_repo import upsert_detail
from cgpe.storage.sqlite_db import connect_sqlite, init_schema
from cgpe.scrape.sources.base import SourceConfig

logger = setup_logger(__name__)


async def backfill_sets(config: SourceConfig) -> None:

    # 1. CONNECT TO SQLITE
    conn = connect_sqlite("data/cgpe.sqlite3")

    # 2. ENSURE TABLES EXIST (safe to call every time)
    init_schema(conn)

    details = []

    connector = aiohttp.TCPConnector(limit=200, limit_per_host=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        set_pages = await run_set_pipeline(
            set_url=config.sets_to_scrape,
            session=session,
            source_config=config
        )
        
        detail_links = []
        for set_page in set_pages:
            detail_links.extend(set_page.detail_links)

        details = await run_detail_pipeline(
            detail_link=detail_links,
            session=session,
            source_config=config
        )

    # 3. STORE RESULTS
    for detail in details:
        upsert_detail(conn, detail.to_db_row())

    logger.info("Backfilling completed. Total details fetched: %d", len(details))

    conn.close()

if __name__ == "__main__":
    import asyncio
    from cgpe.scrape.sources.pokemon import POKEMON_PRICECHARTING

    asyncio.run(backfill_sets(POKEMON_PRICECHARTING))