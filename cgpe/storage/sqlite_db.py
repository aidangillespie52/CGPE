# cgpe/storage/sqlite_db.py

import sqlite3
from pathlib import Path


def connect_sqlite(db_path: str | Path) -> sqlite3.Connection:
    """
    Open a SQLite connection with sane defaults.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    # Good defaults for multi-process-ish / polling workloads
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")  # ms

    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """
    Create tables if they don't exist.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS card_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            card_link TEXT NOT NULL,
            card_name TEXT NOT NULL,
            card_num  TEXT NOT NULL,
            source    TEXT,

            ungraded_price REAL,

            grade7_mean  REAL, grade7_std  REAL,
            grade8_mean  REAL, grade8_std  REAL,
            grade9_mean  REAL, grade9_std  REAL,
            grade10_mean REAL, grade10_std REAL,

            pop_json             TEXT,
            graded_prices_json   TEXT NOT NULL,
            grades_1_to_10_json  TEXT NOT NULL,

            scraped_at TEXT NOT NULL,

            UNIQUE(card_link, source)
        );

        CREATE INDEX IF NOT EXISTS idx_card_details_source_num
            ON card_details(source, card_num);

        CREATE INDEX IF NOT EXISTS idx_card_details_scraped_at
            ON card_details(scraped_at);
        """
    )
    conn.commit()
