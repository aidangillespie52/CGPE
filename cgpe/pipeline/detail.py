# cgpe/pipeline/detail.py

import asyncio
from typing import List, Sequence, Union, overload

import aiohttp

from cgpe.http.client import fetch_html
from cgpe.scrape.pricecharting.detail.parse_detail import Detail, parse_detail_page
from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

@overload
async def run_detail_pipeline(
    session: aiohttp.ClientSession,
    source_config: SourceConfig,
    detail_link: str,
) -> Detail: ...


@overload
async def run_detail_pipeline(
    session: aiohttp.ClientSession,
    source_config: SourceConfig,
    detail_link: Sequence[str],
) -> List[Detail]: ...


async def run_detail_pipeline(
    session: aiohttp.ClientSession,
    source_config: SourceConfig,
    detail_link: Union[str, Sequence[str]],
) -> Union[Detail, List[Detail]]:

    many_links = isinstance(detail_link, Sequence) and not isinstance(detail_link, (str, bytes))
    links: List[str] = list(detail_link) if many_links else [detail_link]  # type: ignore[list-item]

    log.info("Running detail pipeline for %d links", len(links))

    # 1) fetch ALL pages at once
    results = await asyncio.gather(
        *(fetch_html(session, url=l) for l in links),
        return_exceptions=True,
    )

    html_pages = []
    for link, r in zip(links, results):
        if isinstance(r, Exception):
            log.warning("Failed to fetch %s: %r", link, r)
        else:
            html_pages.append(r)

    # 2) parse ALL at once
    details: List[Detail] = await asyncio.gather(
        *(
            asyncio.to_thread(
                parse_detail_page,
                html=html,
                card_link=link,
                source_config=source_config,
            )
            for link, html in zip(links, html_pages)
        )
    )

    if not many_links:
        return details[0]

    return details
