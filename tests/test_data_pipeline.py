import pandas as pd
import pytest

from aml.data import ibm, synthetic
from aml.data.profiles import build_profiles
from aml.data.validate import validate_transactions


@pytest.fixture(scope="module")
def txns() -> pd.DataFrame:
    return ibm.normalize(synthetic.generate(n_accounts=200, n_normal=2_000, seed=7))


def test_normalize_shape_and_order(txns: pd.DataFrame) -> None:
    assert list(txns.columns) == ibm.NORMALIZED_COLUMNS
    assert txns["ts"].is_monotonic_increasing
    assert txns["from_account"].str.contains("-").all()  # bank-prefixed


def test_txn_ids_unique_and_stable(txns: pd.DataFrame) -> None:
    assert txns["txn_id"].is_unique
    again = ibm.normalize(synthetic.generate(n_accounts=200, n_normal=2_000, seed=7))
    assert (again["txn_id"] == txns["txn_id"]).all()  # idempotent loads depend on this


def test_patterns_injected(txns: pd.DataFrame) -> None:
    rate = txns["is_laundering"].mean()
    assert 0 < rate < 0.1
    structuring = txns[txns["is_laundering"] & (txns["payment_format"] == "Cash")]
    assert structuring["amount_paid"].between(9_000, 10_000).all()


def test_validation_quarantines_bad_rows(txns: pd.DataFrame) -> None:
    broken = txns.copy()
    broken.loc[0, "payment_format"] = "Carrier pigeon"
    valid, rejected = validate_transactions(broken)
    assert len(rejected) == 1
    assert "payment_format" in rejected.loc[0, "error"]
    assert len(valid) == len(txns) - 1


def test_profiles_cover_every_account(txns: pd.DataFrame) -> None:
    customers, accounts = build_profiles(txns)
    used = set(txns["from_account"]) | set(txns["to_account"])
    assert set(accounts["account_id"]) == used
    assert customers["customer_id"].is_unique
    assert set(customers["risk_rating"]) <= {"low", "medium", "high"}
    assert (customers["expected_monthly_volume"] >= 500).all()


def test_customer_ids_stable_per_account(txns: pd.DataFrame) -> None:
    _, a1 = build_profiles(txns, seed=1)
    _, a2 = build_profiles(txns.sample(frac=0.5, random_state=0), seed=2)
    merged = a1.merge(a2, on="account_id", suffixes=("_1", "_2"))
    assert (merged["customer_id_1"] == merged["customer_id_2"]).all()


def test_take_window_respects_size(txns: pd.DataFrame) -> None:
    assert len(ibm.take_window(txns, "full")) == len(txns)
