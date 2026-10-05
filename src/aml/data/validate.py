"""Validate a normalized DataFrame against the Transaction contract.

Returns (valid, rejected). Rejected rows keep an `error` column explaining why, so bad data is
quarantined and inspectable instead of silently dropped.
Step 2 reuses this for the dead-letter topic.
"""

from __future__ import annotations

from decimal import Decimal

import pandas as pd
from pydantic import ValidationError

from aml.data.schemas import Transaction


def validate_transactions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    errors: list[str | None] = []
    for rec in df.to_dict(orient="records"):
        try:
            Transaction.model_validate(
                {
                    **rec,
                    "ts": rec["ts"].to_pydatetime(),
                    "amount_paid": Decimal(str(rec["amount_paid"])),
                    "amount_received": Decimal(str(rec["amount_received"])),
                }
            )
            errors.append(None)
        except ValidationError as e:
            errors.append(
                "; ".join(f"{'.'.join(map(str, x['loc']))}: {x['msg']}" for x in e.errors())
            )
    err = pd.Series(errors, index=df.index)
    ok = err.isna()
    rejected = df[~ok].assign(error=err[~ok])
    return df[ok].reset_index(drop=True), rejected.reset_index(drop=True)
