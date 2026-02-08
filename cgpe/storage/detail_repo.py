from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_detail(conn: sqlite3.Connection, row: Dict[str, Any]) -> None:
    def _json(v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            return v  # already dumped
        return json.dumps(v)

    # Ensure scraped_at exists
    row = dict(row)
    row.setdefault("scraped_at", utc_now_iso())

    params = {
        "card_link": row["card_link"],
        "card_name": row["card_name"],
        "card_num": row["card_num"],
        "source": row.get("source"),

        "ungraded_price": row.get("ungraded_price"),

        "grade7_mean": row.get("grade7_mean"),
        "grade7_std": row.get("grade7_std"),
        "grade8_mean": row.get("grade8_mean"),
        "grade8_std": row.get("grade8_std"),
        "grade9_mean": row.get("grade9_mean"),
        "grade9_std": row.get("grade9_std"),
        "grade10_mean": row.get("grade10_mean"),
        "grade10_std": row.get("grade10_std"),

        "pop_json": _json(row.get("pop_json") if "pop_json" in row else row.get("pop")),
        "graded_prices_json": _json(
            row.get("graded_prices_json") if "graded_prices_json" in row else row.get("graded_prices_by_grade")
        ),
        "grades_1_to_10_json": _json(
            row.get("grades_1_to_10_json") if "grades_1_to_10_json" in row else row.get("grades_1_to_10")
        ),

        "scraped_at": row["scraped_at"],
    }

    sql = """
    INSERT INTO card_details (
        card_link, card_name, card_num, source,
        ungraded_price,
        grade7_mean, grade7_std,
        grade8_mean, grade8_std,
        grade9_mean, grade9_std,
        grade10_mean, grade10_std,
        pop_json, graded_prices_json, grades_1_to_10_json,
        scraped_at
    ) VALUES (
        :card_link, :card_name, :card_num, :source,
        :ungraded_price,
        :grade7_mean, :grade7_std,
        :grade8_mean, :grade8_std,
        :grade9_mean, :grade9_std,
        :grade10_mean, :grade10_std,
        :pop_json, :graded_prices_json, :grades_1_to_10_json,
        :scraped_at
    )
    ON CONFLICT(card_link, source) DO UPDATE SET
        card_name=excluded.card_name,
        card_num=excluded.card_num,
        ungraded_price=excluded.ungraded_price,
        grade7_mean=excluded.grade7_mean,
        grade7_std=excluded.grade7_std,
        grade8_mean=excluded.grade8_mean,
        grade8_std=excluded.grade8_std,
        grade9_mean=excluded.grade9_mean,
        grade9_std=excluded.grade9_std,
        grade10_mean=excluded.grade10_mean,
        grade10_std=excluded.grade10_std,
        pop_json=excluded.pop_json,
        graded_prices_json=excluded.graded_prices_json,
        grades_1_to_10_json=excluded.grades_1_to_10_json,
        scraped_at=excluded.scraped_at
    ;
    """
    conn.execute(sql, params)
    conn.commit()


def get_detail_by_link(conn: sqlite3.Connection, *, card_link: str, source: Optional[str] = None) -> Optional[dict]:
    if source is None:
        r = conn.execute("SELECT * FROM card_details WHERE card_link=? ORDER BY scraped_at DESC LIMIT 1", (card_link,)).fetchone()
    else:
        r = conn.execute(
            "SELECT * FROM card_details WHERE card_link=? AND source=? ORDER BY scraped_at DESC LIMIT 1",
            (card_link, source),
        ).fetchone()

    if r is None:
        return None

    d = dict(r)
    # decode JSON fields
    for k in ("pop_json", "graded_prices_json", "grades_1_to_10_json"):
        if d.get(k) is not None:
            d[k] = json.loads(d[k])
    return d
