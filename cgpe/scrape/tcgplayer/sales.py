# cgpe/scrape/tcgplayer/sales.py

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import overload

import aiohttp

from cgpe.http.session import SessionPool, SessionData
from cgpe.http.client import fetch_post  # adjust import path if needed
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

def _normalize_ids(arg: str | Iterable[str]) -> tuple[list[str], bool]:
    if isinstance(arg, str):
        return [arg], True
    return list(arg), False


def build_latest_sales_url(product_id: str) -> str:
    return f"https://mpapi.tcgplayer.com/v2/product/{product_id}/latestsales"


def _headers_from_session(sd: SessionData) -> dict[str, str]:
    cookie = "; ".join(f"{k}={v}" for k, v in sd.cookies.items())
    headers: dict[str, str] = {
        "User-Agent": sd.user_agent,
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://www.tcgplayer.com",
        "Referer": "https://www.tcgplayer.com/",
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


def _get_pool_state(pool: SessionPool) -> tuple[asyncio.Lock, dict[str, int]]:
    lock = getattr(pool, "_tcgplayer_refresh_lock", None)
    counts = getattr(pool, "_tcgplayer_request_counts", None)
    if lock is None:
        lock = asyncio.Lock()
        setattr(pool, "_tcgplayer_refresh_lock", lock)
    if counts is None:
        counts = {}
        setattr(pool, "_tcgplayer_request_counts", counts)
    return lock, counts


@overload
async def fetch_sales_data(
    http_session: aiohttp.ClientSession,
    session_pool: SessionPool,
    product_id: str,
    *,
    pool_key: str = "tcgplayer:anon",
    refresh_every_n: int = 30,
) -> str: ...


@overload
async def fetch_sales_data(
    http_session: aiohttp.ClientSession,
    session_pool: SessionPool,
    product_ids: Iterable[str],
    *,
    pool_key: str = "tcgplayer:anon",
    refresh_every_n: int = 30,
) -> list[str]: ...

async def fetch_sales_data(
    http_session: aiohttp.ClientSession,
    session_pool: SessionPool,
    arg: str | Iterable[str],
    *,
    pool_key: str = "tcgplayer:anon",
    refresh_every_n: int = 30,
) -> str | list[str | None]:

    ids, single = _normalize_ids(arg)
    lock, counts = _get_pool_state(session_pool)

    # single-flight refresh per pool_key (prevents refresh storms)
    refresh_locks = getattr(session_pool, "_refresh_locks", None)
    if refresh_locks is None:
        refresh_locks = session_pool._refresh_locks = {}
    refresh_lock = refresh_locks.setdefault(pool_key, asyncio.Lock())

    async def fetch_one(product_id: str) -> str | None:
        try:
            pid = str(product_id).strip()

            # skip bad ids without killing the whole batch
            if not pid:
                log.warning("Skipping empty product_id: %r", product_id)
                return None
            if not pid.isdigit():
                log.warning("Skipping non-numeric product_id: %r", pid)
                return None

            # ---- claim a "request slot" BEFORE making the request ----
            async with lock:
                next_n = counts.get(pool_key, 0) + 1
                counts[pool_key] = next_n

            # Refresh at the START of each block: 1, 31, 61, ...
            # (so we refresh *before* sending the next batch of N requests)
            do_refresh = refresh_every_n > 0 and ((next_n - 1) % refresh_every_n == 0)

            if do_refresh:
                # ensure only one refresh runs at a time for this pool_key
                async with refresh_lock:
                    # optional: double-check to avoid redundant refresh if many tasks pile up
                    # (not strictly necessary with refresh_lock, but nice)
                    await asyncio.to_thread(session_pool.refresh, pool_key)

            sd: SessionData = session_pool.get(pool_key)
            headers = _headers_from_session(sd)
            url = build_latest_sales_url(pid)

            return await fetch_post(http_session, url, payload={}, headers=headers)

        except RuntimeError as e:
            if "Session is closed" in str(e):
                raise
            log.warning("Runtime error fetching product_id=%r: %s", product_id, e)
            return None
        except Exception as e:
            log.warning("Failed fetching product_id=%r: %s", product_id, e)
            return None

    results: list[str | None] = await asyncio.gather(*(fetch_one(pid) for pid in ids))

    return results[0] if single else results