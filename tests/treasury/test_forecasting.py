from datetime import date
from decimal import Decimal

import pytest

from sigmavault.treasury.ingestion import FinancialRecord
from sigmavault.treasury.forecasting import (
    ExpenseForecast,
    forecast_recurring_expenses,
)


def make_record(
    record_id: str,
    month: int,
    amount: str,
    subcategory: str = "Office rent",
    category: str = "Office Bills",
    currency: str = "XAF",
    due_day: int = 15,
) -> FinancialRecord:
    return FinancialRecord(
        record_id=record_id,
        description=subcategory,
        category=category,
        subcategory=subcategory,
        amount=Decimal(amount),
        currency=currency,
        record_type="expense",
        transaction_date=None,
        due_date=date(2026, month, due_day),
        status="unverified",
        source="forecast",
        project_id="",
        location="Yaounde",
    )


def test_forecasts_fixed_monthly_rent():
    records = [
        make_record(f"RENT-{month}", month, "100000")
        for month in range(4, 10)
    ]

    forecasts = forecast_recurring_expenses(
        records, as_of=date(2026, 10, 1)
    )

    assert len(forecasts) == 1

    forecast = forecasts[0]

    assert isinstance(forecast, ExpenseForecast)
    assert forecast.amount == Decimal("100000")
    assert forecast.currency == "XAF"
    assert forecast.due_date == date(2026, 10, 15)
    assert forecast.source == "forecast"
    assert len(forecast.supporting_record_ids) == 6


def test_uses_median_for_variable_stationery():
    amounts = [
        "18000", "24000", "17000",
        "30000", "22000", "19000",
    ]

    records = [
        make_record(
            f"STAT-{month}",
            month,
            amount,
            subcategory="Stationery",
        )
        for month, amount in zip(range(4, 10), amounts)
    ]

    forecasts = forecast_recurring_expenses(
        records, as_of=date(2026, 10, 1)
    )

    assert len(forecasts) == 1
    assert forecasts[0].amount == Decimal("20500")


def test_does_not_forecast_missing_month():
    records = [
        make_record(f"RENT-{month}", month, "100000")
        for month in range(4, 9)
    ]

    forecasts = forecast_recurring_expenses(
        records, as_of=date(2026, 10, 1)
    )

    assert forecasts == []


def test_excludes_project_based_payroll():
    records = [
        make_record(
            f"ENGINEER-{month}",
            month,
            "500000",
            subcategory="Postsales engineer",
            category="Payroll",
        )
        for month in range(4, 10)
    ]

    forecasts = forecast_recurring_expenses(
        records, as_of=date(2026, 10, 1)
    )

    assert forecasts == []


def test_rejects_currency_mismatch():
    records = [
        make_record(
            f"RENT-{month}",
            month,
            "100000",
            currency="USD" if month == 9 else "XAF",
        )
        for month in range(4, 10)
    ]

    with pytest.raises(ValueError, match="currency"):
        forecast_recurring_expenses(
            records, as_of=date(2026, 10, 1)
        )