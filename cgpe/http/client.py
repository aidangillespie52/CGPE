# cgpe/http/client.py

import asyncio
import random
from typing import Awaitable, TypeVar

import aiohttp

from cgpe.http.headers import build_headers
from cgpe.http.rate_limit import RATE_LIMITER, backoff_seconds
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

T = TypeVar("T")


async def _backoff(attempt: int, resp: aiohttp.ClientResponse) -> None:
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            wait_s = float(retry_after)
        except ValueError:
            wait_s = backoff_seconds(attempt)
    else:
        wait_s = backoff_seconds(attempt)

    # a little extra jitter so multiple workers don't re-hit at the same time
    wait_s += random.uniform(0.0, 0.5)

    log.warning(
        "429 Too Many Requests for %s; backing off %.2fs (attempt=%d)",
        str(resp.url),
        wait_s,
        attempt,
    )
    await asyncio.sleep(wait_s)


async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    *,
    timeout_s: int = 30,
    retries: int = 6,
) -> str:
    timeout = aiohttp.ClientTimeout(total=timeout_s)

    for attempt in range(retries + 1):
        try:
            await RATE_LIMITER.wait()

            async with session.get(
                url,
                headers=build_headers(),  # rotate per request
                timeout=timeout,
            ) as resp:
                # throttling
                if resp.status == 429:
                    await _backoff(attempt, resp)
                    continue

                # transient server errors: retry
                if resp.status in (500, 502, 503, 504):
                    wait_s = backoff_seconds(attempt)
                    log.warning(
                        "Server error %d for %s; retrying in %.2fs (attempt=%d)",
                        resp.status,
                        url,
                        wait_s,
                        attempt,
                    )
                    await asyncio.sleep(wait_s)
                    continue

                resp.raise_for_status()

                text = await resp.text()

                log.debug(
                    "Fetched %d characters from %s (status=%d)",
                    len(text),
                    url,
                    resp.status,
                )

                return text

        except aiohttp.ClientResponseError as e:
            # retry on 429/5xx (sometimes raised by raise_for_status in other flows)
            if e.status in {429, 500, 502, 503, 504} and attempt < retries:
                wait_s = backoff_seconds(attempt)
                log.warning(
                    "HTTP error %s for %s; retrying in %.2fs (attempt=%d/%d)",
                    e.status,
                    url,
                    wait_s,
                    attempt,
                    retries,
                )
                await asyncio.sleep(wait_s)
                continue

            log.warning("HTTP error %s for %s", e.status, url)
            raise

        except asyncio.TimeoutError:
            if attempt < retries:
                wait_s = backoff_seconds(attempt)
                log.warning(
                    "Timeout while fetching %s; retrying in %.2fs (attempt=%d/%d)",
                    url,
                    wait_s,
                    attempt,
                    retries,
                )
                await asyncio.sleep(wait_s)
                continue

            log.warning("Timeout while fetching %s (giving up)", url)
            raise

        except Exception:
            log.exception("Unexpected error while fetching %s", url)
            raise

    raise RuntimeError(f"Failed to fetch after {retries} retries: {url}")


async def limited(sem: asyncio.Semaphore, coro: Awaitable[T]) -> T:
    # sem._value is private; safe enough for debug logs but don't rely on it
    log.debug("Waiting for semaphore (value=%s)", getattr(sem, "_value", "?"))

    async with sem:
        log.debug("Semaphore acquired (value=%s)", getattr(sem, "_value", "?"))
        try:
            return await coro
        finally:
            log.debug("Semaphore released (value=%s)", getattr(sem, "_value", "?"))
