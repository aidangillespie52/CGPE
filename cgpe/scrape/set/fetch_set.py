# cgpe/scrape/set/fetch_set.py

from typing import Any, Dict, List
from urllib.parse import urlencode
import aiohttp
import json

from cgpe.http.client import fetch_html
from cgpe.logging.logger import setup_logger
from cgpe.config.scraper import ScraperConfig

scraper_config = ScraperConfig()
log = setup_logger(__name__)


async def fetch_json_list(
        session: aiohttp.ClientSession,
        url: str,
        params: dict | None = None,
    ) -> List[Dict[str, Any]]:

    full_url = f"{url}?{urlencode(params)}"
    log.debug("Fetching JSON data from: %s", full_url)
    data = await fetch_html(session, full_url)
   
    data = '[' + data + ']'  # Wrap in list to ensure consistent shape
    data = json.loads(data)
    data = data[0]['products']

    if not data:
        return []
    
    log.debug("Fetched data type: %s", type(data))
    log.debug("Fetched %d records", len(data))

    return data


async def fetch_set_json_pages(
        session: aiohttp.ClientSession,
        set_url: str
    ) -> List[Dict[str, Any]]:

    log.info("Starting set fetch (JSON cursor pagination mode)")
    log.debug("Base set URL: %s", set_url)

    all_rows: List[Dict[str, Any]] = []
    cursor = 0

    while cursor <= scraper_config.max_cursor:
        params = {
            "sort": "",
            "when": "none",
            "cursor": cursor,
            "format": "json",
        }

        log.debug("Requesting cursor=%d", cursor)

        try:
            page_data = await fetch_json_list(
                session=session,
                url=set_url,
                params=params
            )

            log.debug("Fetched cursor=%d (%d records)", cursor, len(page_data))

            # ---- termination condition ----
            if len(page_data) == 0:
                log.info("Termination condition met at cursor=%d (len == 1)", cursor)
                break

            all_rows.extend(page_data)
            cursor += 50

        except Exception:
            log.exception("Set fetch failed at cursor=%d", cursor)
            raise

    log.info("Set fetch completed: %d total records collected", len(all_rows))
    return all_rows
