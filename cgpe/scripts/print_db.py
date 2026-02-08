# cgpe/scripts/print_db.py

import sqlite3
from pathlib import Path


DB_PATH = Path("data/cgpe.sqlite3")


def print_all_tables(conn: sqlite3.Connection) -> None:
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()

    if not tables:
        print("No tables found.")
        return

    for (table_name,) in tables:
        print("\n" + "=" * 80)
        print(f"TABLE: {table_name}")
        print("=" * 80)

        rows = conn.execute(f"SELECT * FROM {table_name};").fetchall()
        if not rows:
            print("(no rows)")
            continue

        # Print column headers
        col_names = rows[0].keys()
        print(" | ".join(col_names))
        print("-" * 80)

        for row in rows:
            values = []
            for v in row:
                if isinstance(v, str) and len(v) > 120:
                    v = v[:117] + "..."
                values.append(str(v))
            print(" | ".join(values))


def main() -> None:
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print(f"Database: {DB_PATH.resolve()}")
    print_all_tables(conn)

    conn.close()


if __name__ == "__main__":
    main()
