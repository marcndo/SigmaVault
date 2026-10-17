from datetime import date
from decimal import Decimal

import pytest

from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)


def make_record(**overrides):
    values = {
        "identity": SourceRecordIdentity(
            provider="csv",
            namespace="test-account",
            record_id="101",
        ),
        "description": "Office supplies",
        "category": "Operations",
        "subcategory": "",
        "amount": Decimal("25000"),
        "currency": "XAF",
        "direction": "expense",
        "transaction_date": date(2026, 10, 1),
        "due_date": None,
        "status": "paid",
        "source": "confirmed",
    }
    values.update(overrides)
    return CanonicalFinancialRecord(**values)


def test_canonical_record_preserves_financial_data():
    record = make_record()

    assert record.amount == Decimal("25000")
    assert record.identity.provider == "csv"
    assert record.direction == "expense"


def test_same_record_id_in_different_sources_has_different_identity():
    csv_identity = SourceRecordIdentity("csv", "account-1", "101")
    firefly_identity = SourceRecordIdentity(
        "firefly", "account-1", "101"
    )

    assert csv_identity != firefly_identity


@pytest.mark.parametrize(
    "amount",
    [Decimal("0"), Decimal("-1"), Decimal("NaN")],
)
def test_invalid_amounts_are_rejected(amount):
    with pytest.raises(ValueError):
        make_record(amount=amount)


def test_paid_record_requires_transaction_date():
    with pytest.raises(ValueError):
        make_record(transaction_date=None)


def test_unpaid_record_cannot_have_payment_date():
    with pytest.raises(ValueError):
        make_record(status="unpaid")