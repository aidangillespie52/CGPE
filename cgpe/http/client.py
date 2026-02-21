# cgpe/http/client.py

import asyncio
import random
from typing import Awaitable, TypeVar, Dict, Any, Literal

import aiohttp

from cgpe.http.headers import build_headers
from cgpe.http.rate_limit import RATE_LIMITER, backoff_seconds
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

T = TypeVar("T")

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


async def _backoff(attempt: int, resp: aiohttp.ClientResponse) -> None:
    retry_after = resp.headers.get("Retry-After")
    if retry_after:
        try:
            wait_s = float(retry_after)
        except ValueError:
            wait_s = backoff_seconds(attempt)
    else:
        wait_s = backoff_seconds(attempt)

    wait_s += random.uniform(0.0, 0.5)

    reason = resp.reason or "Unknown"
    log.warning("HTTP %d %s for %s; backing off %.2fs (attempt=%d)", resp.status, reason, str(resp.url), wait_s, attempt)

    try:
        await asyncio.sleep(wait_s)
    except asyncio.CancelledError:
        log.debug("Backoff sleep cancelled for %s", str(resp.url))
        raise


async def _fetch(
    session: aiohttp.ClientSession,
    method: Literal["GET", "POST"],
    url: str,
    headers: Dict[str, str] | None = None,
    payload: Dict[str, Any] | None = None,
    *,
    timeout_s: int = 30,
    retries: int = 6,
) -> str:
    """Core fetch logic shared by fetch_html and fetch_json_post."""
    timeout = aiohttp.ClientTimeout(total=timeout_s)
    headers = headers or {}

    kwargs: Dict[str, Any] = {
        "headers": build_headers(headers),
        "timeout": timeout,
    }
    if method == "POST" and payload is not None:
        kwargs["json"] = payload

    for attempt in range(retries + 1):
        try:
            await RATE_LIMITER.wait()
            resp = await session.request(method, url, **kwargs).__aenter__()
        except asyncio.TimeoutError:
            if attempt < retries:
                wait_s = backoff_seconds(attempt)
                log.warning("Timeout while fetching %s; retrying in %.2fs (attempt=%d/%d)", url, wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                continue
            log.warning("Timeout while fetching %s (giving up)", url)
            raise
        except Exception:
            log.exception("Unexpected error while fetching %s", url)
            raise

        try:
            if resp.status == 429:
                await _backoff(attempt, resp)
                continue

            if resp.status in (500, 502, 503, 504):
                wait_s = backoff_seconds(attempt)
                log.warning("Server error %d for %s; retrying in %.2fs (attempt=%d)", resp.status, url, wait_s, attempt)
                await asyncio.sleep(wait_s)
                continue

            resp.raise_for_status()
            text = await resp.text()
        except aiohttp.ClientResponseError as e:
            if e.status in _RETRYABLE_STATUSES and attempt < retries:
                wait_s = backoff_seconds(attempt)
                log.warning("HTTP error %s for %s; retrying in %.2fs (attempt=%d/%d)", e.status, url, wait_s, attempt, retries)
                await asyncio.sleep(wait_s)
                continue
            log.warning("HTTP error %s for %s", e.status, url)
            raise
        finally:
            await resp.__aexit__(None, None, None)

        log.debug("Fetched %d characters from %s (status=%d, method=%s)", len(text), url, resp.status, method)
        return text

    raise RuntimeError(f"Failed to fetch after {retries} retries: {url}")


async def fetch_html(
    session: aiohttp.ClientSession,
    url: str,
    headers: Dict[str, str] | None = None,
    *,
    timeout_s: int = 30,
    retries: int = 6,
) -> str:
    return await _fetch(
        session, "GET", url, headers,
        timeout_s=timeout_s, retries=retries,
    )


async def fetch_post(
    session: aiohttp.ClientSession,
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str] | None = None,
    *,
    timeout_s: int = 30,
    retries: int = 6,
) -> str:
    return await _fetch(
        session, "POST", url, headers, payload,
        timeout_s=timeout_s, retries=retries,
    )


async def limited(sem: asyncio.Semaphore, coro: Awaitable[T]) -> T:
    log.debug("Waiting for semaphore (value=%s)", getattr(sem, "_value", "?"))

    async with sem:
        log.debug("Semaphore acquired (value=%s)", getattr(sem, "_value", "?"))
        try:
            return await coro
        finally:
            log.debug("Semaphore released (value=%s)", getattr(sem, "_value", "?"))