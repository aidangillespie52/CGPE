# cgpe/pipeline/set.py

import asyncio
from typing import List, Sequence, Union, overload

import aiohttp

from cgpe.scrape.sources.base import SourceConfig
from cgpe.scrape.set.fetch_set import fetch_set_json_pages
from cgpe.scrape.set.parse_set import parse_set_data, SetPage

@overload
async def run_set_pipeline(
    session: aiohttp.ClientSession,
    set_url: str,
    source_config: SourceConfig,
) -> List[dict]: ...


@overload
async def run_set_pipeline(
    session: aiohttp.ClientSession,
    set_url: Sequence[str],
    source_config: SourceConfig,
) -> List[List[dict]]: ...


async def run_set_pipeline(
    session: aiohttp.ClientSession,
    set_url: Union[str, Sequence[str]],
    source_config: SourceConfig,
) -> Union[SetPage, List[SetPage]]:

    many_urls = isinstance(set_url, Sequence) and not isinstance(set_url, (str, bytes))
    urls: List[str] = list(set_url) if many_urls else [set_url]  # type: ignore[list-item]

    # 1) fetch ALL sets at once
    datas: List[List[dict]] = await asyncio.gather(
        *(fetch_set_json_pages(session=session, set_url=url) for url in urls)
    )

    # 2) parse ALL at once
    parsed: List[List[dict]] = await asyncio.gather(
        *(
            asyncio.to_thread(
                parse_set_data,
                data=data,
                set_link=url,
                source_config=source_config,
            )
            for url, data in zip(urls, datas)
        )
    )

    if not many_urls:
        return parsed[0]

    return parsed
