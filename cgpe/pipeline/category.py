# cgpe/pipeline/category.py

from __future__ import annotations

import aiohttp
from typing import Iterable, List, Union, overload

from cgpe.scrape.sources.base import SourceConfig
from cgpe.scrape.category.parse_category import parse_category_page, CategoryPage
from cgpe.http.client import fetch_html
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


@overload
async def run_category_pipeline(
    session: aiohttp.ClientSession,
    source_config: SourceConfig,
) -> CategoryPage: ...


@overload
async def run_category_pipeline(
    session: aiohttp.ClientSession,
    source_config: Iterable[SourceConfig],
) -> List[CategoryPage]: ...


async def run_category_pipeline(
    session: aiohttp.ClientSession,
    source_config: Union[SourceConfig, Iterable[SourceConfig]],
) -> Union[CategoryPage, List[CategoryPage]]:

    # Normalize to list
    many = isinstance(source_config, Iterable) and not isinstance(source_config, (str, bytes))
    configs = list(source_config) if many else [source_config]  # type: ignore[list-item]

    pages: List[CategoryPage] = []
    for cfg in configs:
        log.debug("Fetching category page: %s", cfg.category_link)

        html = await fetch_html(session, url=cfg.category_link)

        pages.append(
            parse_category_page(
                html=html,
                source_config=cfg,
            )
        )

    return pages if many else pages[0]
