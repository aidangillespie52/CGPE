# cgpe/cli/profit.py
from __future__ import annotations

import argparse
import asyncio
from dataclasses import asdict
from typing import Optional, List, Tuple

import aiohttp

from cgpe.http.client import fetch_html, limited
from cgpe.http.header_rotator import HeaderRotator

from cgpe.pipeline.set import run_set_pipeline
from cgpe.pipeline.detail import run_detail_pipeline
from cgpe.scrape.detail.parse_detail import parse_detail_page
from cgpe.scrape.sources.base import SourceConfig
from cgpe.analysis.profit_analysis import calculate_profit
from cgpe.analysis.expected_value import expected_value_from_population_and_prices
from cgpe.logging.logger import setup_logger

log = setup_logger(__name__)

def _fmt_money(x: Optional[float]) -> str:
    if x is None:
        return "-"
    return f"${x:,.2f}"

async def fetch_with_url(session, sem, url: str):
    log.info("Fetching detail page: %r", url)
    html = await limited(sem, fetch_html(session, url=url))
    log.info("Fetched detail page: %r (length=%d)", url, len(html))
    return url, html


async def run_profit_report_for_set(
    set_url: str,
    config: SourceConfig,
    *,
    max_concurrency: int = 3,
) -> List[tuple]:

    sem = asyncio.Semaphore(max_concurrency)
    rows: list[tuple] = []

    async with aiohttp.ClientSession() as session:
        # 1) set -> detail urls
        set_page = await limited(sem, run_set_pipeline(session, set_url, config))
        detail_urls = set_page.detail_links

        # dedupe preserve order
        seen = set()
        detail_urls = [u for u in detail_urls if not (u in seen or seen.add(u))]

        log.info("Found %d detail urls", len(detail_urls))

        # 2) fetch concurrently
        tasks = [asyncio.create_task(fetch_with_url(session, sem, u)) for u in detail_urls]

        # 3) process as they complete; parse in a thread
        for fut in asyncio.as_completed(tasks):
            try:
                url, html = await fut
            except Exception as e:
                log.warning("fetch failed: %r", e)
                continue

            try:
                # offload CPU-bound parsing
                r = await asyncio.to_thread(parse_detail_page, html, url, config)
            except Exception as e:
                log.warning("parse failed for %s: %r", url, e)
                continue

            if not r.pop or not r.grades_1_to_10 or r.ungraded_price is None:
                log.warning("Skipping incomplete detail data: %r", r.card_link)
                continue

            ev = expected_value_from_population_and_prices(
                population=r.pop.get("psa"),
                prices=r.grades_1_to_10,
            )

            profit = calculate_profit(r.ungraded_price, ev)

            log.info("%s, %s", r.card_link, profit)

            if profit is not None:
                log.info(
                    "Card %r: cost=%s, ev=%s, profit=%s",
                    getattr(r, "card_name", ""),
                    _fmt_money(r.ungraded_price),
                    _fmt_money(ev),
                    _fmt_money(profit),
                )
                rows.append((r, ev, r.ungraded_price, profit))

    return rows


def print_profit_table(rows: List[tuple], *, min_profit: float = 0.0, limit: int = 200) -> None:
    # filter + sort
    profitable = [
        (d, ev, cost, profit)
        for (d, ev, cost, profit) in rows
        if profit is not None and profit >= min_profit
    ]
    profitable.sort(key=lambda x: x[3], reverse=True)

    if not profitable:
        print("No profitable cards found with the current rules.")
        return

    # header
    print('\n')
    print(f"{'CARD':50}  {'COST':>10}  {'EV':>10}  {'PROFIT':>10}  {'URL'}")
    print("-" * 110)

    for (d, ev, cost, profit) in profitable[:limit]:
        name = getattr(d, "card_name", "")[:50]
        url = getattr(d, "card_link", "")
        print(f"{name:50}  {_fmt_money(cost):>10}  {_fmt_money(ev):>10}  {_fmt_money(profit):>10}  {url}")

    if len(profitable) > limit:
        print(f"\n... and {len(profitable) - limit} more")


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cgpe-profit",
        description="Given a set link, fetch details and report profitable cards.",
    )
    p.add_argument("set_url", help="PriceCharting set URL (e.g. https://www.pricecharting.com/console/pokemon-XYZ?view=table)")
    p.add_argument("--min-profit", type=float, default=0.0, help="Only show cards with profit >= this amount (default: 0)")
    p.add_argument("--concurrency", type=int, default=3, help="Max concurrent detail fetches (default: 3)")
    p.add_argument("--limit", type=int, default=200, help="Max rows to print (default: 200)")
    return p


async def _amain(args) -> int:
    # IMPORTANT: you must pass the concrete SourceConfig instance you already use elsewhere
    # If you have multiple sources, build/choose the right one here.
    config = args.config  # set below in main()

    rows = await run_profit_report_for_set(
        args.set_url,
        config=config,
        max_concurrency=args.concurrency,
    )

    print_profit_table(rows, min_profit=args.min_profit, limit=args.limit)
    return 0


def main() -> int:
    parser = build_argparser()
    args = parser.parse_args()

    try:
        from cgpe.scrape.sources.pokemon import POKEMON_PRICECHARTING  # adjust if needed
        args.config = POKEMON_PRICECHARTING
    except Exception as e:
        raise SystemExit(
            "Could not import a default config. Wire your SourceConfig instance in cgpe/cli/profit.py main()."
        ) from e

    return asyncio.run(_amain(args))


if __name__ == "__main__":
    raise SystemExit(main())
