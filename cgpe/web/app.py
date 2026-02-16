# cgpe/web/app.py

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from cgpe.storage.sqlite_db import connect_sqlite
from cgpe.storage.detail_repo import get_detail_by_link
from cgpe.storage.queries.web_search import search_card_details
from cgpe.web.services.profit_board import iter_all_details, top_by_profit

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = "data/cgpe.sqlite3"

app = FastAPI(title="CGPE Web")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def search_page(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})


@app.get("/api/search")
def search_api(q: str = Query(...), source: Optional[str] = None, limit: int = 25):
    rows = search_card_details(q=q, source=source, limit=limit)
    return {"query": q, "count": len(rows), "rows": rows}


@app.get("/card", response_class=HTMLResponse)
def card_page(request: Request, link: str = Query(...), source: Optional[str] = None):
    conn = connect_sqlite(DB_PATH)
    try:
        card = get_detail_by_link(conn, card_link=link, source=source)
        if not card:
            raise HTTPException(404, "Card not found")
    finally:
        conn.close()

    return templates.TemplateResponse("card.html", {"request": request, "card": card.to_db_row()})


@app.get("/api/card")
def card_api(link: str = Query(...), source: Optional[str] = None):
    conn = connect_sqlite(DB_PATH)
    try:
        card = get_detail_by_link(conn, card_link=link, source=source)
        if not card:
            raise HTTPException(404, "Card not found")
        
        return card.to_db_row()
    finally:
        conn.close()


@app.get("/profit", response_class=HTMLResponse)
def profit_page(request: Request):
    return templates.TemplateResponse("profit.html", {"request": request})


@app.get("/api/profit")
def profit_api(source: Optional[str] = None, limit: int = 100):
    conn = connect_sqlite(DB_PATH)
    try:
        scanned, it = iter_all_details(conn, source=source)
        rows = top_by_profit(it, limit=limit)
        return {"count": len(rows), "scanned": scanned, "rows": rows}
    finally:
        conn.close()
