# cgpe/web/services/profit_board.py

from typing import Iterable, List, Optional, Set, Tuple
from fastapi import HTTPException

from cgpe.web.services.enrich import enrich_detail

_REQUIRED_COLS: Set[str] = {
    "card_link",
    "ungraded_price",
    "graded_prices_json",
    "pop_json",
}

_NICE_TO_HAVE: Set[str] = {
    "card_name",
    "card_num",
    "card_img_link",
    "source",
    "grade10_mean",
}


def _list_tables(conn) -> List[str]:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    return [r[0] for r in cur.fetchall()]


def _table_columns(conn, table: str) -> Set[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return {r[1] for r in cur.fetchall()}


def _detect_details_table(conn) -> str:
    best_score = -1
    best_table = ""

    for t in _list_tables(conn):
        cols = _table_columns(conn, t)
        if not _REQUIRED_COLS.issubset(cols):
            continue
        score = len(cols.intersection(_NICE_TO_HAVE))
        if score > best_score:
            best_score = score
            best_table = t

    if not best_table:
        raise HTTPException(
            status_code=500,
            detail="Could not find details table with required columns",
        )

    return best_table


def iter_all_details(conn, *, source: Optional[str] = None) -> Tuple[int, Iterable[dict]]:
    table = _detect_details_table(conn)
    cols = _table_columns(conn, table)

    select_cols = [c for c in (*_REQUIRED_COLS, *_NICE_TO_HAVE) if c in cols]
    sql = ", ".join(select_cols)

    cur = conn.cursor()
    if source and "source" in cols:
        cur.execute(f"SELECT {sql} FROM {table} WHERE source = ?", (source,))
    else:
        cur.execute(f"SELECT {sql} FROM {table}")

    names = [d[0] for d in cur.description]
    rows = (dict(zip(names, r)) for r in cur.fetchall())

    cur.execute(f"SELECT COUNT(1) FROM {table}")
    scanned = cur.fetchone()[0]

    return scanned, rows


def _profit_value(d: dict) -> float:
    try:
        p = float(d.get("expected_profit"))
        return p if p == p else float("-inf")
    except Exception:
        return float("-inf")


def top_by_profit(details: Iterable[dict], *, limit: int) -> List[dict]:
    rows: List[dict] = []
    for d in details:
        try:
            rows.append(enrich_detail(d))
        except Exception:
            continue

    rows.sort(key=_profit_value, reverse=True)
    return [r for r in rows if _profit_value(r) != float("-inf")][:limit]
