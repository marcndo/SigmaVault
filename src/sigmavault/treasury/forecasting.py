from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from statistics import median


RECURRING_EXPENSES = {
    ("Office Bills", "Office rent"),
    ("Office Bills", "Internet"),
    ("Office Bills", "Stationery"),
    ("Payroll", "Cleaner"),
}


@dataclass(frozen=True)
class ExpenseForecast:
    category: str
    subcategory: str
    amount: Decimal
    currency: str
    due_date: date
    source: str
    supporting_record_ids: tuple[str, ...]
    explanation: str


def _previous_months(as_of: date, count: int) -> list[tuple[int, int]]:
    """Return the previous `count` calendar months, oldest first."""
    months = []
    year, month = as_of.year, as_of.month

    for _ in range(count):
        month -= 1

        if month == 0:
            month = 12
            year -= 1

        months.append((year, month))

    return list(reversed(months))


def forecast_recurring_expenses(
    records: Sequence,
    as_of: date,
    months_required: int = 6,
) -> list[ExpenseForecast]:

    if not isinstance(as_of, date):
        raise TypeError("as_of must be a date")

    if as_of.day != 1:
        raise ValueError("as_of must be the first day of a month")

    if months_required <= 0:
        raise ValueError("months_required must be positive")

    historical_months = _previous_months(as_of, months_required)
    expected_months = set(historical_months)

    grouped = defaultdict(list)

    for record in records:
        key = (record.category, record.subcategory)

        if record.record_type != "expense":
            continue

        if key not in RECURRING_EXPENSES:
            continue

        if record.status == "cancelled":
            continue

        if record.due_date is None:
            continue

        month_key = (
            record.due_date.year,
            record.due_date.month,
        )

        if month_key not in expected_months:
            continue

        grouped[key].append(record)

    forecasts = []

    for (category, subcategory), group in sorted(grouped.items()):

        monthly_records = defaultdict(list)

        for record in group:
            month_key = (
                record.due_date.year,
                record.due_date.month,
            )
            monthly_records[month_key].append(record)

        # Every required month must have exactly one record.
        if any(
            len(monthly_records[month]) != 1
            for month in historical_months
        ):
            continue

        ordered_records = [
            monthly_records[month][0]
            for month in historical_months
        ]

        currencies = {record.currency for record in ordered_records}

        if len(currencies) != 1:
            raise ValueError(
                f"{subcategory}: currency mismatch"
            )

        amounts = [record.amount for record in ordered_records]
        due_days = [record.due_date.day for record in ordered_records]

        forecast_amount = median(amounts)
        forecast_day = int(median(due_days))

        # Cap the day to the final day of the forecast month.
        from calendar import monthrange

        last_day = monthrange(as_of.year, as_of.month)[1]
        forecast_day = min(forecast_day, last_day)

        forecast_due_date = date(
            as_of.year,
            as_of.month,
            forecast_day,
        )

        supporting_ids = tuple(
            record.record_id for record in ordered_records
        )

        explanation = (
            f"Estimated {subcategory} using the median amount "
            f"from {months_required} consecutive monthly records. "
            f"Expected due day estimated from historical dates. "
            f"Source records may be unverified."
        )

        forecasts.append(
            ExpenseForecast(
                category=category,
                subcategory=subcategory,
                amount=forecast_amount,
                currency=ordered_records[0].currency,
                due_date=forecast_due_date,
                source="forecast",
                supporting_record_ids=supporting_ids,
                explanation=explanation,
            )
        )

    return forecasts