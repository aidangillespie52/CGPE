# cgpe/pipeline/detail_pipeline.py

import aiohttp
import asyncio

from cgpe.scrape.detail.parse_detail import Detail, parse_detail_page
from cgpe.http.client import fetch_html
from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


async def run_detail_pipeline(
        session: aiohttp.ClientSession,
        config: SourceConfig,
        detail_link: str
    ) -> Detail:

    log.info("Starting detail pipeline")
    log.debug("Fetching detail page: %s", detail_link)

    try:
        html = await fetch_html(
            session,
            url=detail_link
        )

        log.debug(
            "Fetched detail HTML (%d characters) for %s",
            len(html),
            detail_link,
        )

        detail = parse_detail_page(
            html=html,
            card_link=detail_link,
            source_config=config,
        )

        log.info("Parsed detail page successfully: %s", detail_link)

        return detail

    except Exception:
        log.exception("Detail pipeline failed for %s", detail_link)
        raise


if __name__ == "__main__":
    from cgpe.scrape.sources.pokemon import POKEMON_PRICECHARTING

    async def main():
        async with aiohttp.ClientSession() as session:
            detail = await run_detail_pipeline(
                session=session,
                config=POKEMON_PRICECHARTING,
                detail_link="https://www.pricecharting.com/game/pokemon-paldean-fates/nemona-238",
                headers={},
            )
            print(detail)

    asyncio.run(main())
