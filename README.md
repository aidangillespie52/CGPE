# CGPE — Card Grading Profitability Engine

CGPE is a data pipeline and web app for analyzing the **expected value and profitability of grading trading cards** (currently focused on Pokémon).

It scrapes raw market data, normalizes it into a consistent schema, computes expected value using population and price distributions, and surfaces the most profitable cards via a FastAPI web interface.

---

## Features

- 🔍 Concurrent scraping with `aiohttp`
- 🧮 Expected value modeling using population + price data
- 💾 SQLite persistence with a single-source-of-truth `Detail` model
- 📊 Profit ranking (highest → lowest expected profit)
- 🌐 FastAPI web UI (search, card view, profit board)
- 🧱 Clean separation of models, services, storage, and web layers

---

## Project Structure

```text
CGPE/
├─ arbitrage/            # (optional) arbitrage-related experiments/tools
├─ cgpe/                 # main package
│  ├─ analysis/          # expected value + profit calculations
│  ├─ cli/               # command-line entrypoints
│  ├─ config/            # config objects + scraper settings
│  ├─ http/              # fetching, headers, rate limiting, retries
│  ├─ logging/           # logger setup
│  ├─ models/            # core domain models (Detail, Set, etc.)
│  ├─ pipeline/          # orchestration of scrape → parse → persist steps
│  ├─ scrape/            # site-specific parsing + scrape helpers
│  │  ├─ index/          # “what sets exist” / discovery lists
│  │  ├─ category/       # category/list page parsing
│  │  ├─ set/            # set page parsing
│  │  ├─ detail/         # detail page parsing
│  │  └─ sources/        # per-source configuration + adapters
│  ├─ scripts/           # one-off utilities (db inspection, etc.)
│  ├─ services/          # long-running jobs / backfills
│  ├─ storage/           # DB layer (repos + SQL queries)
│  ├─ utils/             # shared helpers
│  └─ web/               # FastAPI app + UI (templates/static)
├─ data/                 # sqlite db + local data artifacts
├─ logs/                 # runtime logs
├─ Dockerfile
├─ pyproject.toml
├─ README.md
└─ uv.lock

