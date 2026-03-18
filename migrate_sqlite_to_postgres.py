import argparse
import sqlite3
from typing import Dict, List, Sequence, Tuple

import psycopg
from psycopg.rows import dict_row


TABLE_ORDER: Sequence[str] = (
    "review",
    "reviewers",
    "studies",
    "exclusion_reasons",
    "first_screening",
    "first_screening_conflicts",
    "second_screening",
    "second_screening_conflicts",
)

IDENTITY_TABLES: Sequence[Tuple[str, str]] = (
    ("review", "id"),
    ("reviewers", "id"),
    ("studies", "id"),
    ("exclusion_reasons", "id"),
)


def sqlite_rows(sqlite_path: str, table: str) -> List[Dict]:
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(f"SELECT * FROM {table};")
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def pg_columns(pg_conn, table: str) -> List[str]:
    rows = pg_conn.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position;
        """,
        (table,),
    ).fetchall()
    return [r["column_name"] for r in rows]


def insert_rows(pg_conn, table: str, rows: List[Dict], wipe: bool):
    if wipe:
        # Wipe in dependency-safe order: we do this once at start elsewhere.
        pass

    if not rows:
        return

    pg_cols = pg_columns(pg_conn, table)
    if not pg_cols:
        raise RuntimeError(f"Table '{table}' not found in PostgreSQL. Run init_db() first.")

    # Insert only columns that exist in both DBs (robust to schema evolution)
    common_cols = [c for c in rows[0].keys() if c in pg_cols]
    if not common_cols:
        return

    cols_sql = ", ".join(common_cols)
    placeholders = ", ".join(["%s"] * len(common_cols))
    sql = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders});"

    values = []
    for r in rows:
        values.append(tuple(r.get(c) for c in common_cols))

    with pg_conn.cursor() as cur:
        cur.executemany(sql, values)


def reset_sequences(pg_conn):
    for table, col in IDENTITY_TABLES:
        pg_conn.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence(%s, %s),
                COALESCE((SELECT MAX({col}) FROM {table}), 1),
                (SELECT MAX({col}) IS NOT NULL FROM {table})
            );
            """,
            (table, col),
        )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sqlite", required=True, help="Path to the existing SQLite database (e.g., instance/review.db)")
    ap.add_argument("--pg", required=True, help="PostgreSQL DSN (e.g., postgresql://user:pass@host:5432/dbname)")
    ap.add_argument("--wipe", action="store_true", help="TRUNCATE all tables before importing (recommended)")
    args = ap.parse_args()

    with psycopg.connect(args.pg, row_factory=dict_row) as pg_conn:
        if args.wipe:
            # TRUNCATE in reverse dependency order to avoid FK errors
            for t in reversed(TABLE_ORDER):
                pg_conn.execute(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE;")

        for table in TABLE_ORDER:
            rows = sqlite_rows(args.sqlite, table)
            insert_rows(pg_conn, table, rows, wipe=False)
            pg_conn.commit()
            print(f"{table}: {len(rows)} rows imported")

        reset_sequences(pg_conn)
        pg_conn.commit()
        print("Done. Sequences reset.")


if __name__ == "__main__":
    main()
