from collections.abc import Sequence

from sigmavault.pipeline.models import CanonicalFinancialRecord
from sigmavault.treasury.domain import Money
from sigmavault.treasury.upcoming_obligations import UpcomingBill


def csv_records_to_upcoming_bills(
    records: Sequence[CanonicalFinancialRecord],
) -> list[UpcomingBill]:
    """Convert eligible CSV liabilities into advisory upcoming bills."""

    bills: list[UpcomingBill] = []
    seen: set[tuple[str, str, str]] = set()

    for record in records:
        identity = record.identity
        key = (
            identity.provider,
            identity.namespace,
            identity.record_id,
        )

        if key in seen:
            raise ValueError("Duplicate financial record identity")

        seen.add(key)

        if record.direction != "expense":
            continue

        if record.status != "unpaid":
            continue

        if record.due_date is None:
            continue

        if record.currency != "XAF":
            raise ValueError(
                "CSV treasury assessment currently supports XAF only"
            )

        bill_status = (
            "scheduled"
            if record.source == "confirmed"
            else "estimated"
        )

        bills.append(
            UpcomingBill(
                bill_id=f"{identity.provider}:{identity.namespace}:{identity.record_id}",
                name=record.description,
                amount=Money(record.amount, record.currency),
                due_date=record.due_date,
                status=bill_status,
            )
        )

    return bills