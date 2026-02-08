# cgpe/pipeline/category_pipeline.py

import aiohttp

from cgpe.scrape.sources.pokemon import SourceConfig
from cgpe.scrape.category.parse_category import parse_category_page, CategoryPage
from cgpe.http.client import fetch_html
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


async def run_category_pipeline(
        session: aiohttp.ClientSession,
        source_config: SourceConfig
    ) -> CategoryPage:
    
    log.info("Starting category pipeline")

    log.debug(
        "Fetching category page: %s",
        source_config.category_link,
    )

    html = await fetch_html(
        session,
        url=source_config.category_link
    )

    log.debug(
        "Fetched category HTML (%d characters)",
        len(html),
    )

    category_page = parse_category_page(
        html=html,
        source_config=source_config,
    )

    log.info(
        "Parsed category page: %d set links discovered",
        len(category_page.set_links),
    )

    return category_page
