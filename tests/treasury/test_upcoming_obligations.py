from datetime import date
from decimal import Decimal

import pytest

from sigmavault.treasury.domain import Money, ObligationSource
from sigmavault.treasury.upcoming_obligations import (
    UpcomingBill,
    confirmed_obligations,
)


def test_confirmed_bill_becomes_obligation():
    bill = UpcomingBill(
        bill_id="rent-oct-2026",
        name="Office rent",
        amount=Money(Decimal("75000"), "XAF"),
        due_date=date(2026, 10, 20),
        status="confirmed",
    )

    obligations = confirmed_obligations([bill])

    assert len(obligations) == 1
    assert obligations[0].amount.amount == Decimal("75000")
    assert obligations[0].source == ObligationSource.CONFIRMED


def test_unconfirmed_bills_are_not_misrepresented_as_confirmed():
    bills = [
        UpcomingBill(
            bill_id="internet-oct-2026",
            name="Internet",
            amount=Money(Decimal("15000"), "XAF"),
            due_date=date(2026, 10, 22),
            status="scheduled",
        ),
        UpcomingBill(
            bill_id="travel-oct-2026",
            name="Travel",
            amount=Money(Decimal("30000"), "XAF"),
            due_date=date(2026, 10, 25),
            status="estimated",
        ),
    ]

    assert confirmed_obligations(bills) == []


@pytest.mark.parametrize("amount", ["0", "-100", "NaN", "Infinity"])
def test_invalid_bill_amount_is_rejected(amount):
    with pytest.raises(ValueError):
        UpcomingBill(
            bill_id="invalid",
            name="Invalid bill",
            amount=Money(Decimal(amount), "XAF"),
            due_date=date(2026, 10, 20),
            status="confirmed",
        )