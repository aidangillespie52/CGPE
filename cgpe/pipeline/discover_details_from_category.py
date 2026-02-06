# cgpe/pipeline/discover_details_from_category.py

import aiohttp
from typing import List
import asyncio

from cgpe.http.header_rotator import HeaderRotator
from cgpe.scrape.sources.base import SourceConfig
from cgpe.pipeline.category_pipeline import run_category_pipeline
from cgpe.pipeline.set_pipeline import run_set_pipeline
from cgpe.pipeline.detail_pipeline import run_detail_pipeline
from cgpe.scrape.detail.parse_detail import Detail
from cgpe.http.client import limited
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


async def run_discover_details_from_category(
    session: aiohttp.ClientSession,
    config: SourceConfig,
) -> List[Detail]:
    log.info("Starting discover-details-from-category pipeline")

    header_rotator = HeaderRotator()
    sem = asyncio.Semaphore(4)

    # ---- CATEGORY ----
    category_page = await run_category_pipeline(
        session,
        config,
        headers=header_rotator.next(),
    )

    log.info(
        "Category page fetched: %d set links discovered",
        len(category_page.set_links),
    )

    # ---- SET PAGES ----
    log.info("Fetching set pages")
    tasks = [
        asyncio.create_task(
            limited(
                sem,
                run_set_pipeline(
                    session,
                    u,
                    config,
                    headers=header_rotator.next(),
                ),
            )
        )
        for u in category_page.set_links[:5]
    ]

    set_pages_results = await asyncio.gather(*tasks, return_exceptions=True)

    set_pages = []
    failed_sets = 0
    for r in set_pages_results:
        if isinstance(r, Exception):
            failed_sets += 1
            log.warning("Set pipeline failed: %r", r)
            continue
        set_pages.append(r)

    log.info(
        "Set pages completed: %d succeeded, %d failed",
        len(set_pages),
        failed_sets,
    )

    # ---- DETAIL LINKS ----
    detail_links = [
        link
        for set_page in set_pages
        for link in set_page.detail_links
    ]

    log.info("Discovered %d detail links", len(detail_links))

    # ---- DETAIL PAGES ----
    log.info("Fetching detail pages")
    tasks = [
        asyncio.create_task(
            limited(
                sem,
                run_detail_pipeline(
                    session,
                    config,
                    u,
                    headers=header_rotator.next(),
                ),
            )
        )
        for u in detail_links
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    detail_pages = []
    failed_details = 0
    for r in results:
        if isinstance(r, Exception):
            failed_details += 1
            log.warning("Detail pipeline failed: %r", r)
            continue
        detail_pages.append(r)

    log.info(
        "Detail pages completed: %d succeeded, %d failed",
        len(detail_pages),
        failed_details,
    )

    log.info(
        "Discover-details pipeline finished: %d total detail pages",
        len(detail_pages),
    )

    return detail_pages


async def main():
    from cgpe.scrape.sources.pokemon import POKEMON_PRICECHARTING

    config = POKEMON_PRICECHARTING

    async with aiohttp.ClientSession() as session:
        details = await run_discover_details_from_category(session, config)
        log.info("Pipeline produced %d detail objects", len(details))


if __name__ == "__main__":
    asyncio.run(main())
