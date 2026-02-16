# cgpe/storage/detail_repo.py
from __future__ import annotations

import sqlite3
from typing import Any, Dict, Optional, Union

from cgpe.models.detail import Detail


def upsert_detail(conn: sqlite3.Connection, row: Union[Detail, Dict[str, Any]]) -> None:
    if isinstance(row, Detail):
        detail = row
    else:
        # if it looks like a DB row, convert it
        detail = Detail.from_db_row(row) if "grade7_mean" in row else Detail(**row)

    conn.execute(Detail.upsert_sql(), detail.to_db_row())
    conn.commit()


def get_detail_by_link(
    conn: sqlite3.Connection,
    *,
    card_link: str,
    source: Optional[str] = None,
) -> Optional[Detail]:
    if source is None:
        r = conn.execute(
            f"SELECT * FROM {Detail.TABLE} WHERE card_link=? ORDER BY scraped_at DESC LIMIT 1",
            (card_link,),
        ).fetchone()
    else:
        r = conn.execute(
            f"SELECT * FROM {Detail.TABLE} WHERE card_link=? AND source=? ORDER BY scraped_at DESC LIMIT 1",
            (card_link, source),
        ).fetchone()

    return Detail.from_db_row(dict(r)) if r else None
