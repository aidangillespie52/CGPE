# cgpe/web/services/profit_board.py
from __future__ import annotations

from typing import Iterable, List, Optional, Tuple


def iter_all_details(conn, *, source: Optional[str] = None) -> Tuple[int, Iterable[dict]]:
    cur = conn.cursor()

    where = "WHERE source = ?" if source else ""
    args = (source,) if source else ()

    scanned = cur.execute(f"SELECT COUNT(1) FROM card_details {where}", args).fetchone()[0]

    cur.execute(f"SELECT * FROM card_details {where}", args)
    names = [d[0] for d in cur.description]
    rows = (dict(zip(names, r)) for r in cur.fetchall())

    return scanned, rows


def top_by_profit(details: Iterable[dict], *, limit: int) -> List[dict]:
    def key(d: dict) -> float:
        try:
            p = float(d.get("expected_profit"))
            return p if p == p else float("-inf")
        except Exception:
            return float("-inf")

    rows = sorted(details, key=key, reverse=True)
    return [d for d in rows if key(d) != float("-inf")][:limit]
