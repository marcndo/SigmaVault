from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)
from sigmavault.treasury.csv_obligations import (
    csv_records_to_upcoming_bills,
)


def make_record(**overrides):
    record = CanonicalFinancialRecord(
        identity=SourceRecordIdentity(
            provider="csv",
            namespace="obsec-pilot",
            record_id="EXP-001",
        ),
        description="Office rent",
        category="Operations",
        subcategory="Rent",
        amount=Decimal("50000"),
        currency="XAF",
        direction="expense",
        transaction_date=None,
        due_date=date(2026, 10, 25),
        status="unpaid",
        source="confirmed",
    )
    return replace(record, **overrides)


def test_unpaid_confirmed_expense_becomes_scheduled_bill():
    bills = csv_records_to_upcoming_bills([make_record()])

    assert len(bills) == 1
    assert bills[0].amount.amount == Decimal("50000")
    assert bills[0].status == "scheduled"
    assert bills[0].due_date == date(2026, 10, 25)


def test_forecast_expense_becomes_estimated_bill():
    bills = csv_records_to_upcoming_bills([
        make_record(source="forecast")
    ])

    assert bills[0].status == "estimated"


@pytest.mark.parametrize(
    "changes",
    [
        {"status": "paid", "transaction_date": date(2026, 10, 10)},
        {"status": "cancelled"},
        {"status": "unverified"},
        {"direction": "income"},
        {"due_date": None},
    ],
)
def test_ineligible_records_are_not_upcoming_bills(changes):
    bills = csv_records_to_upcoming_bills([
        make_record(**changes)
    ])

    assert bills == []


def test_duplicate_identity_is_rejected():
    record = make_record()

    with pytest.raises(ValueError, match="Duplicate financial record identity"):
        csv_records_to_upcoming_bills([record, record])


def test_non_xaf_liability_is_rejected():
    with pytest.raises(ValueError, match="supports XAF only"):
        csv_records_to_upcoming_bills([
            make_record(currency="USD")
        ])