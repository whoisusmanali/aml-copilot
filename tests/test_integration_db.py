"""Integration tests: need `make up-lite` (or `make up`) and `make data-synthetic` first."""

import psycopg
import pytest

from aml.config import get_settings
from aml.data.load import load_all

pytestmark = pytest.mark.integration


def test_load_is_idempotent() -> None:
    s = get_settings()
    load_all(s.postgres_dsn, s.processed_dir)
    second = load_all(s.postgres_dsn, s.processed_dir)
    assert second == {"customers": 0, "accounts": 0, "transactions": 0}


def test_audit_log_is_append_only() -> None:
    with psycopg.connect(get_settings().postgres_dsn) as conn:
        conn.execute(
            "INSERT INTO cases.audit_log (actor, entity, action) VALUES ('test', 'case:0', 'ping')"
        )
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute("DELETE FROM cases.audit_log")
