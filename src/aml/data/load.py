"""Load prepared Parquet files into Postgres, idempotently.

Pattern: COPY into a temporary staging table (fast), then
INSERT ... ON CONFLICT DO NOTHING into the real table (safe to re-run).
Running `make load` twice leaves exactly the same rows.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from pathlib import Path

import pandas as pd
import psycopg

TABLES: dict[str, tuple[str, str]] = {
    # file stem -> (target table, conflict key)
    "customers": ("ref.customers", "customer_id"),
    "accounts": ("ref.accounts", "account_id"),
    "transactions": ("raw.transactions", "txn_id"),
}


def _copy_frame(cur: psycopg.Cursor, table: str, key: str, df: pd.DataFrame) -> int:
    cols: Sequence[str] = list(df.columns)
    col_list = ", ".join(cols)
    cur.execute(f"CREATE TEMP TABLE stage (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
    with cur.copy(f"COPY stage ({col_list}) FROM STDIN") as copy:
        for row in df.itertuples(index=False, name=None):
            copy.write_row(row)
    cur.execute(
        f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM stage "
        f"ON CONFLICT ({key}) DO NOTHING"
    )
    return int(cur.rowcount)


def load_all(dsn: str, processed_dir: Path) -> dict[str, int]:
    """Load customers, accounts, then transactions (FK order). Returns rows inserted per table."""
    inserted: dict[str, int] = {}
    with psycopg.connect(dsn) as conn:
        for stem, (table, key) in TABLES.items():
            path = processed_dir / f"{stem}.parquet"
            if not path.exists():
                raise FileNotFoundError(f"{path} missing - run `make data` first")
            df = pd.read_parquet(path)
            t0 = time.perf_counter()
            with conn.transaction(), conn.cursor() as cur:
                inserted[stem] = _copy_frame(cur, table, key, df)
            print(
                f"{table:<20} {len(df):>9,} rows read, {inserted[stem]:>9,} new "
                f"({time.perf_counter() - t0:.1f}s)"
            )
    return inserted
