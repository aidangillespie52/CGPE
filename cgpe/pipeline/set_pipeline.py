# cgpe/pipeline/set_pipeline.py

import aiohttp
from typing import List
import json

from cgpe.scrape.sources.base import SourceConfig
from cgpe.logging.logger import setup_logger
from cgpe.config.scraper import ScraperConfig
from cgpe.scrape.set.fetch_set import fetch_set_json_pages
from cgpe.scrape.set.parse_set import parse_set_data
from cgpe.http.header_rotator import HeaderRotator

log = setup_logger(__name__)
scraper_config = ScraperConfig()

async def fetch_json(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    params: dict,
) -> List[dict]:
    async with session.get(url, headers=headers, params=params) as resp:
        resp.raise_for_status()
        return await resp.json()


async def run_set_pipeline(
        session: aiohttp.ClientSession,
        set_url: str,
        source_config: SourceConfig
    ) -> List[dict]:

    data = await fetch_set_json_pages(
        session = session,
        set_url = set_url
    )

    return parse_set_data(
        data=data,
        set_link=set_url,
        source_config=source_config,
    )

async def example():
    headers_rotator = HeaderRotator()
    from cgpe.scrape.sources.pokemon import POKEMON_PRICECHARTING

    async with aiohttp.ClientSession() as session:
        source_config = POKEMON_PRICECHARTING
        set_url = "https://www.pricecharting.com/console/pokemon-black-bolt"

        result = await run_set_pipeline(
            session=session,
            set_url=set_url,
            source_config=source_config
        )

        print(len(result.detail_links))

if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
        