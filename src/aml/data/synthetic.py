"""Small synthetic generator in IBM raw format.

Used by tests and CI (no Kaggle download needed), and for quick local experiments.
It injects three classic laundering typologies so later steps have something to find:
  - structuring: several cash deposits just under the 10,000 reporting threshold
  - fan-out:     one account sprays funds to many mules within hours
  - cycle:       funds travel A -> B -> C -> A and return to the origin
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from aml.data.ibm import RAW_COLUMNS

FORMATS = ["ACH", "Wire", "Credit Card", "Cheque", "Cash"]
FORMAT_P = [0.40, 0.15, 0.25, 0.10, 0.10]


def _acct(rng: np.random.Generator) -> tuple[str, str]:
    bank = f"{rng.integers(1, 40):03d}"
    acct = f"{rng.integers(0x10000000, 0xFFFFFFFF):08X}"
    return bank, acct


def generate(
    n_accounts: int = 500, n_normal: int = 5_000, n_patterns: int = 10, seed: int = 42
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2022, 9, 1)
    accounts = [_acct(rng) for _ in range(n_accounts)]
    rows: list[list[object]] = []

    def add(
        ts: datetime, a: tuple[str, str], b: tuple[str, str], amt: float, fmt: str, bad: bool
    ) -> None:
        amt = round(amt, 2)
        rows.append(
            [
                ts.strftime("%Y/%m/%d %H:%M"),
                a[0],
                a[1],
                b[0],
                b[1],
                amt,
                "US Dollar",
                amt,
                "US Dollar",
                fmt,
                int(bad),
            ]
        )

    # Normal traffic: log-normal amounts, random pairs over 30 days.
    for _ in range(n_normal):
        i, j = rng.choice(n_accounts, size=2, replace=False)
        ts = start + timedelta(minutes=int(rng.integers(0, 30 * 24 * 60)))
        fmt = str(rng.choice(FORMATS, p=FORMAT_P))
        add(ts, accounts[i], accounts[j], float(rng.lognormal(6.5, 1.2)), fmt, False)

    # Injected laundering patterns.
    for p in range(n_patterns):
        ts = start + timedelta(days=int(rng.integers(1, 28)), hours=int(rng.integers(0, 20)))
        kind = p % 3
        if kind == 0:  # structuring
            i, j = rng.choice(n_accounts, size=2, replace=False)
            src, dst = accounts[i], accounts[j]
            for k in range(int(rng.integers(3, 6))):
                add(
                    ts + timedelta(hours=3 * k),
                    src,
                    dst,
                    float(rng.uniform(9_000, 9_950)),
                    "Cash",
                    True,
                )
        elif kind == 1:  # fan-out
            src = accounts[rng.integers(n_accounts)]
            for k in range(int(rng.integers(5, 10))):
                mule = accounts[rng.integers(n_accounts)]
                add(
                    ts + timedelta(minutes=20 * k),
                    src,
                    mule,
                    float(rng.uniform(2_000, 8_000)),
                    "Wire",
                    True,
                )
        else:  # cycle
            idx = rng.choice(n_accounts, size=3, replace=False)
            amt = float(rng.uniform(20_000, 60_000))
            path = [accounts[i] for i in idx] + [accounts[idx[0]]]
            for k in range(3):
                add(ts + timedelta(hours=k), path[k], path[k + 1], amt * (0.98**k), "ACH", True)

    df = pd.DataFrame(rows, columns=RAW_COLUMNS)
    return df.sort_values("timestamp", kind="stable").reset_index(drop=True)
