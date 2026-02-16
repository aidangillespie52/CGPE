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
cgpe/
├─ scripts/              # one-off utilities (db inspection, etc.)
├─ services/             # orchestration jobs (e.g. backfills)
│  └─ backfill_sets.py
├─ storage/              # database access layer
│  ├─ detail_repo.py
│  ├─ sqlite_db.py
│  └─ queries/
│     └─ web_search.py
├─ utils/                # shared helpers
│  ├─ json.py
│  └─ time.py
├─ web/                  # FastAPI app + UI
│  ├─ app.py
│  ├─ services/          # business logic for web
│  │  ├─ enrich.py
│  │  └─ profit_board.py
│  ├─ static/
│  │  └─ search.css
│  └─ templates/
│     ├─ search.html
│     ├─ card.html
│     └─ profit.html
├─ data/
│  └─ cgpe.sqlite3       # SQLite database
└─ logs/
   └─ cgpe.log*
