import csv
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


REQUIRED_COLUMNS = {
    "id", "description", "category", "subcategory",
    "amount", "currency", "type", "transaction_date",
    "due_date", "status", "source", "project_id", "location",
}

VALID_TYPES = {"income", "expense"}
VALID_STATUSES = {"paid", "unpaid", "cancelled", "unverified"}
VALID_SOURCES = {"confirmed", "forecast"}


@dataclass(frozen=True)
class FinancialRecord:
    record_id: str
    description: str
    category: str
    subcategory: str
    amount: Decimal
    currency: str
    record_type: str
    transaction_date: date | None
    due_date: date | None
    status: str
    source: str
    project_id: str
    location: str


def parse_date(value: str, row_number: int) -> date | None:
    if not value:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"row {row_number}: invalid date"
        ) from exc


def load_financial_records(path: Path) -> list[FinancialRecord]:
    records = []
    seen_ids = set()

    with Path(path).open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError("CSV has no header")

        if not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError("CSV is missing required columns")

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise ValueError(
                    f"row {row_number}: unexpected extra columns"
                )

            def field(name: str) -> str:
                value = row.get(name)
                if value is None:
                    raise ValueError(
                        f"row {row_number}: missing {name}"
                    )
                return value.strip()

            record_id = field("id")

            if not record_id:
                raise ValueError(
                    f"row {row_number}: empty ID"
                )

            if record_id in seen_ids:
                raise ValueError(
                    f"row {row_number}: duplicate ID"
                )

            seen_ids.add(record_id)

            try:
                amount = Decimal(field("amount"))
            except InvalidOperation as exc:
                raise ValueError(
                    f"row {row_number}: invalid amount"
                ) from exc

            if not amount.is_finite() or amount <= 0:
                raise ValueError(
                    f"row {row_number}: invalid amount"
                )

            record_type = field("type").lower()
            status = field("status").lower()
            source = field("source").lower()

            if record_type not in VALID_TYPES:
                raise ValueError(
                    f"row {row_number}: invalid type"
                )

            if status not in VALID_STATUSES:
                raise ValueError(
                    f"row {row_number}: invalid status"
                )

            if source not in VALID_SOURCES:
                raise ValueError(
                    f"row {row_number}: invalid source"
                )

            currency = field("currency").upper()

            if not currency:
                raise ValueError(
                    f"row {row_number}: missing currency"
                )

            description = field("description")
            category = field("category")

            if not description or not category:
                raise ValueError(
                    f"row {row_number}: missing description or category"
                )

            transaction_date = parse_date(
                field("transaction_date"), row_number
            )
            due_date = parse_date(
                field("due_date"), row_number
            )

            if status == "paid" and transaction_date is None:
                raise ValueError(
                    f"row {row_number}: paid record requires payment date"
                )

            if status == "unpaid" and transaction_date is not None:
                raise ValueError(
                    f"row {row_number}: unpaid record has payment date"
                )

            records.append(
                FinancialRecord(
                    record_id=record_id,
                    description=description,
                    category=category,
                    subcategory=field("subcategory"),
                    amount=amount,
                    currency=currency,
                    record_type=record_type,
                    transaction_date=transaction_date,
                    due_date=due_date,
                    status=status,
                    source=source,
                    project_id=field("project_id"),
                    location=field("location"),
                )
            )

    return records