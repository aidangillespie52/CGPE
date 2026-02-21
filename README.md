# CGPE — Card Grading Profitability Engine

CGPE is a **data pipeline, analysis engine, and web app** for identifying **profitable trading cards to grade**, currently focused on Pokémon.

It scrapes public market data, normalizes it into a stable schema, computes expected value using **population and price distributions**, and exposes results via both a **queryable database** and a **FastAPI web interface**. The system is designed to support future **signal generation** and **arbitrage research**, not automated execution.

---

## What CGPE Does

- Discovers sets, categories, and individual cards
- Scrapes raw population + pricing data concurrently
- Normalizes volatile HTML into stable domain models
- Persists results into SQLite as a single source of truth
- Computes expected value and profitability metrics
- Surfaces profitable cards via search and ranking views

**What it does *not* do (by design):**
- Place trades
- Auto-buy or auto-sell cards
- Circumvent site protections

---

## Key Features

- 🔍 **Concurrent scraping** using `aiohttp`
- 🧠 **Expected value modeling** from real population + price distributions
- 💾 **SQLite persistence** with repository-style access
- 🧱 **Clear separation of concerns** (scrape → pipeline → storage → analysis)
- 🌐 **FastAPI web app** (search, card view, profit board)
- 📊 **Profit ranking & filtering**
- 📡 **Signals & arbitrage research hooks** (non-executing)

---

## Project Structure

```text
CGPE/
├─ cgpe/                     # main package
│  ├─ analysis/              # EV + profitability calculations
│  ├─ cli/                   # command-line tools
│  ├─ config/                # scraper & source configuration
│  ├─ http/                  # HTTP client, headers, rate limiting
│  ├─ logging/               # structured logging
│  ├─ models/                # core domain models (Detail, Set, etc.)
│  ├─ pipeline/              # orchestration: scrape → parse → persist
│  ├─ scrape/                # site-specific scraping & parsing
│  │  ├─ index/              # discovery (what sets exist)
│  │  ├─ category/           # category/list pages
│  │  ├─ set/                # set pages
│  │  ├─ detail/             # individual card pages
│  │  └─ sources/            # per-site adapters & configs
│  ├─ scripts/               # utilities (DB inspection, debugging)
│  ├─ services/              # long-running jobs (backfills, refreshes)
│  ├─ signals/               # arbitrage & profitability signal research
│  ├─ storage/               # DB layer (repos, queries, sqlite)
│  ├─ utils/                 # shared helpers
│  └─ web/                   # FastAPI app + UI
│     ├─ services/           # web-facing service logic
│     ├─ templates/          # Jinja templates
│     └─ static/             # CSS / assets
├─ arbitrage/                # experimental arbitrage research
├─ data/                     # SQLite database
├─ logs/                     # rotating logs
├─ downloaded_files/         # transient runtime artifacts
├─ Dockerfile
├─ pyproject.toml
├─ uv.lock
└─ README.md