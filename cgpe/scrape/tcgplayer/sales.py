# cgpe/scrape/tcgplayer/sales.py

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import overload

import aiohttp

from cgpe.http.session import SessionPool, SessionData
from cgpe.http.client import fetch_post  # adjust import path if needed


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
) -> str | list[str]:

    ids, single = _normalize_ids(arg)
    lock, counts = _get_pool_state(session_pool)

    results: list[str] = []
    for product_id in ids:
        # refresh gating (counts per HTTP request)
        do_refresh = False
        async with lock:
            counts[pool_key] = counts.get(pool_key, 0) + 1
            do_refresh = refresh_every_n > 0 and (counts[pool_key] % refresh_every_n == 0)

        if do_refresh:
            # refresh() is blocking (selenium + time.sleep) -> offload to thread
            await asyncio.to_thread(session_pool.refresh, pool_key)

        sd: SessionData = session_pool.get(pool_key)
        headers = _headers_from_session(sd)
        url = build_latest_sales_url(product_id)

        text = await fetch_post(http_session, url, payload={}, headers=headers)
        results.append(text)

    return results[0] if single else results