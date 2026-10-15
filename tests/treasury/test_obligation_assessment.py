from datetime import date, timedelta
from decimal import Decimal

import pytest

from sigmavault.treasury.domain import Money
from sigmavault.treasury.obligation_assessment import (
    assess_upcoming_obligations,
)
from sigmavault.treasury.upcoming_obligations import UpcomingBill


def make_bill(
    bill_id: str,
    amount: str,
    due_date: date,
    status: str = "confirmed",
) -> UpcomingBill:
    return UpcomingBill(
        bill_id=bill_id,
        name=bill_id,
        amount=Money(Decimal(amount), "XAF"),
        due_date=due_date,
        status=status,
    )


def test_confirmed_bills_reduce_deployable_surplus():
    assessment = assess_upcoming_obligations(
        bills=[
            make_bill("rent", "50000", date(2026, 10, 20)),
            make_bill("internet", "15000", date(2026, 10, 25)),
        ],
        forecasts=[],
        available_cash=Money(Decimal("100000"), "XAF"),
        minimum_buffer=Money(Decimal("20000"), "XAF"),
        planning_horizon=timedelta(days=30),
        as_of=date(2026, 10, 15),
    )

    assert assessment.position.required_liquidity.amount == Decimal("65000")
    assert assessment.position.deployable_surplus.amount == Decimal("15000")
    assert assessment.requires_human_review is True
    assert assessment.forecast_coverage_available is False


def test_scheduled_bill_is_included_conservatively():
    assessment = assess_upcoming_obligations(
        bills=[
            make_bill(
                "scheduled-payroll",
                "90000",
                date(2026, 10, 20),
                status="scheduled",
            ),
        ],
        forecasts=[],
        available_cash=Money(Decimal("100000"), "XAF"),
        minimum_buffer=Money(Decimal("20000"), "XAF"),
        planning_horizon=timedelta(days=30),
        as_of=date(2026, 10, 15),
    )

    assert assessment.position.required_liquidity.amount == Decimal("90000")
    assert assessment.position.liquidity_shortfall.amount == Decimal("10000")


def test_duplicate_bill_ids_are_rejected():
    bills = [
        make_bill("rent", "50000", date(2026, 10, 20)),
        make_bill("rent", "50000", date(2026, 10, 20)),
    ]

    with pytest.raises(ValueError, match="Duplicate"):
        assess_upcoming_obligations(
            bills=bills,
            forecasts=[],
            available_cash=Money(Decimal("100000"), "XAF"),
            minimum_buffer=Money(Decimal("20000"), "XAF"),
            planning_horizon=timedelta(days=30),
            as_of=date(2026, 10, 15),
        )