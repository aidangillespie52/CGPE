# cgpe/storage/queries/web_search.py

import re
from typing import Any, Optional
from rapidfuzz import fuzz
import sqlite3

from cgpe.storage.sqlite_db import connect_sqlite


_NUM_RE = re.compile(r"(?i)\b#?\s*([a-z]{0,4}\s*\d{1,4}(?:\s*/\s*\d{1,4})?)\b")


def _norm(s: str) -> str:
    return " ".join(s.lower().strip().split())


def _extract_num(q: str) -> Optional[str]:
    m = _NUM_RE.search(q)
    if not m:
        return None
    return _norm(m.group(1)).replace(" ", "")


def _strip_num(q: str) -> str:
    return _norm(_NUM_RE.sub(" ", q))


def search_card_details(
    *,
    conn: sqlite3.Connection,
    q: str,
    source: Optional[str] = None,
    limit: int = 25,
    candidate_limit: int = 250,
) -> list[dict[str, Any]]:
    
    q_raw = q or ""
    q_num = _extract_num(q_raw)
    q_text = _strip_num(q_raw)

    if not q_num and not q_text:
        return []

    where = []
    params: list[Any] = []

    if source:
        where.append("source = ?")
        params.append(source)

    like = []
    if q_num:
        like.append("REPLACE(LOWER(card_num), ' ', '') LIKE ?")
        params.append(f"%{q_num}%")
    if q_text:
        like.append("LOWER(card_name) LIKE ?")
        params.append(f"%{q_text}%")

    where.append("(" + " OR ".join(like) + ")")
    where_sql = " WHERE " + " AND ".join(where)

    sql = f"""
        SELECT
            id, card_link, card_name, card_num, source, card_img_link,
            ungraded_price,
            grade7_mean, grade8_mean, grade9_mean, grade10_mean,
            scraped_at
        FROM card_details
        {where_sql}
        ORDER BY scraped_at DESC
        LIMIT ?
    """

    rows = conn.execute(sql, [*params, candidate_limit]).fetchall()

    scored: list[tuple[float, dict[str, Any]]] = []
    for r in rows:
        name = _norm(r["card_name"])
        num = _norm(r["card_num"]).replace(" ", "")

        name_score = fuzz.token_set_ratio(q_text, name) if q_text else 0
        num_score = fuzz.partial_ratio(q_num, num) if q_num else 0

        if q_num and q_text:
            score = 0.65 * num_score + 0.35 * name_score
        elif q_num:
            score = num_score
        else:
            score = name_score

        scored.append((score, dict(r)))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [row for score, row in scored if score >= 55][:limit]
