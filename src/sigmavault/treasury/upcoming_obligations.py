from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

from sigmavault.treasury.domain import Money, Obligation, ObligationSource


BillStatus = Literal["confirmed", "scheduled", "estimated"]


@dataclass(frozen=True)
class UpcomingBill:
    bill_id: str
    name: str
    amount: Money
    due_date: date
    status: BillStatus

    def __post_init__(self) -> None:
        if not self.bill_id.strip():
            raise ValueError("bill_id must not be empty")

        if not self.name.strip():
            raise ValueError("name must not be empty")

        if not self.amount.amount.is_finite():
            raise ValueError("bill amount must be finite")

        if self.amount.amount <= Decimal("0"):
            raise ValueError("bill amount must be positive")

        if self.status not in {"confirmed", "scheduled", "estimated"}:
            raise ValueError("invalid bill status")


def confirmed_obligations(
    bills: list[UpcomingBill],
) -> list[Obligation]:
    """Convert confirmed bills into treasury obligations."""
    return [
        Obligation(
            amount=bill.amount,
            due_date=bill.due_date,
            source=ObligationSource.CONFIRMED,
        )
        for bill in bills
        if bill.status == "confirmed"
    ]