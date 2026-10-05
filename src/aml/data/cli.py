"""Data command line.

aml-data prepare --source synthetic            # no download needed
aml-data prepare --source ibm --size small     # needs data/raw/HI-Small_Trans.csv
aml-data load                                  # into Postgres (needs `make up`)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from aml.config import get_settings
from aml.data import ibm, synthetic
from aml.data.load import load_all
from aml.data.profiles import build_profiles
from aml.data.validate import validate_transactions

IBM_FILE = "HI-Small_Trans.csv"


def prepare(source: str, size: ibm.Size, raw_file: Path | None) -> None:
    s = get_settings()
    t0 = time.perf_counter()

    if source == "synthetic":
        raw = synthetic.generate(seed=s.random_seed)
    else:
        path = raw_file or s.raw_dir / IBM_FILE
        if not path.exists():
            sys.exit(f"{path} not found. Run `make download` or pass --file.")
        # Read a little more than needed: some rows get dropped during normalization.
        n = ibm.SIZES[size]
        raw = ibm.read_raw(path, nrows=None if n is None else int(n * 1.05))

    txns = ibm.take_window(ibm.normalize(raw), size if source == "ibm" else "full")
    valid, rejected = validate_transactions(txns)
    customers, accounts = build_profiles(valid, seed=s.random_seed)

    out = s.processed_dir
    out.mkdir(parents=True, exist_ok=True)
    valid.to_parquet(out / "transactions.parquet", index=False)
    customers.to_parquet(out / "customers.parquet", index=False)
    accounts.to_parquet(out / "accounts.parquet", index=False)
    rejected.to_parquet(out / "rejected.parquet", index=False)

    print(f"source={source} size={size}")
    print(f"  transactions: {len(valid):,} valid, {len(rejected):,} rejected")
    print(
        f"  laundering:   {int(valid['is_laundering'].sum()):,} "
        f"({valid['is_laundering'].mean():.3%})"
    )
    print(f"  customers:    {len(customers):,}")
    print(f"  time window:  {valid['ts'].min()} -> {valid['ts'].max()}")
    print(f"  wrote {out}/ in {time.perf_counter() - t0:.1f}s")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="aml-data")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("prepare", help="normalize, validate, build profiles -> Parquet")
    pp.add_argument("--source", choices=["synthetic", "ibm"], default="synthetic")
    pp.add_argument("--size", choices=list(ibm.SIZES), default="small")
    pp.add_argument("--file", type=Path, default=None)

    sub.add_parser("load", help="load Parquet into Postgres (idempotent)")

    args = p.parse_args(argv)
    if args.cmd == "prepare":
        prepare(args.source, args.size, args.file)
    else:
        s = get_settings()
        load_all(s.postgres_dsn, s.processed_dir)


if __name__ == "__main__":
    main()
