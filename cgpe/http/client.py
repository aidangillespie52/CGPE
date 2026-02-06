# cgpe/http/client.py

import aiohttp
import asyncio
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)


async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    timeout: aiohttp.ClientTimeout | None = None,
) -> str:
    log.debug("HTTP GET %s", url)

    try:
        async with session.get(url, headers=headers, timeout=timeout) as resp:
            log.debug(
                "Response %s for %s (content-type=%s)",
                resp.status,
                url,
                resp.headers.get("Content-Type"),
            )

            resp.raise_for_status()
            text = await resp.text()

            log.debug(
                "Fetched %d characters from %s",
                len(text),
                url,
            )

            return text

    except aiohttp.ClientResponseError as e:
        log.warning(
            "HTTP error %s for %s",
            e.status,
            url,
        )
        raise

    except asyncio.TimeoutError:
        log.warning("Timeout while fetching %s", url)
        raise

    except Exception:
        log.exception("Unexpected error while fetching %s", url)
        raise


async def limited(sem: asyncio.Semaphore, coro):
    log.debug("Waiting for semaphore (value=%d)", sem._value)

    async with sem:
        log.debug("Semaphore acquired (value=%d)", sem._value)
        try:
            return await coro
        finally:
            log.debug("Semaphore released (value=%d)", sem._value)
