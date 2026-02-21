# cgpe/storage/sqlite_db.py

import sqlite3
from pathlib import Path
from typing import Iterable, Type


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;",
        (table,),
    ).fetchone()
    return row is not None


def _existing_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table});").fetchall()
    return {r["name"] for r in rows}


def _create_table_sql(model: Type) -> str:
    col_defs = ",\n            ".join(
        f"{name} {ddl}" for name, ddl in model.DDL_COLUMNS.items()
    )

    unique_defs = []
    for cols in getattr(model, "UNIQUE_CONSTRAINTS", []) or []:
        unique_defs.append(f"UNIQUE({', '.join(cols)})")

    uniques = ""
    if unique_defs:
        uniques = ",\n            " + ",\n            ".join(unique_defs)

    return f"""
        CREATE TABLE IF NOT EXISTS {model.TABLE} (
            {col_defs}
            {uniques}
        );
    """.strip()


def _ensure_indexes(conn: sqlite3.Connection, model: Type) -> None:
    for name, cols in getattr(model, "INDEXES", []) or []:
        cols_sql = ", ".join(cols)
        conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {model.TABLE}({cols_sql});")


def sync_schema(conn: sqlite3.Connection, models: Iterable[Type]) -> None:
    """
    Forward-only schema sync:
      - create missing tables
      - add missing columns
      - create missing indexes
    Never drops/renames columns automatically.
    """
    with conn:
        for m in models:
            if not hasattr(m, "TABLE") or not hasattr(m, "DDL_COLUMNS"):
                raise ValueError(f"Model {m} missing TABLE / DDL_COLUMNS")

            if not _table_exists(conn, m.TABLE):
                conn.executescript(_create_table_sql(m))
                _ensure_indexes(conn, m)
                continue

            existing = _existing_columns(conn, m.TABLE)

            for col, ddl in m.DDL_COLUMNS.items():
                if col in existing:
                    continue

                # SQLite limitations: can't add PK via ALTER TABLE
                if "PRIMARY KEY" in ddl.upper():
                    raise ValueError(f"Cannot ALTER ADD PRIMARY KEY column: {m.TABLE}.{col}")

                conn.execute(f"ALTER TABLE {m.TABLE} ADD COLUMN {col} {ddl};")

            _ensure_indexes(conn, m)

def connect_sqlite(db_path: str | Path) -> sqlite3.Connection:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")

    return conn