from datetime import date
from decimal import Decimal
from datetime import timedelta

import pytest

from sigmavault.treasury.assessment import (
    forecasts_to_obligations,
)

from sigmavault.treasury.assessment import (
    assess_forecast_liquidity,
)
from sigmavault.treasury.domain import Money
from sigmavault.treasury.domain import ObligationSource
from sigmavault.treasury.forecasting import ExpenseForecast


def make_forecast(source="forecast"):
    return ExpenseForecast(
        category="Office Bills",
        subcategory="Office rent",
        amount=Decimal("100000"),
        currency="XAF",
        due_date=date(2026, 10, 15),
        source=source,
        supporting_record_ids=(
            "RENT-APR",
            "RENT-MAY",
            "RENT-JUN",
            "RENT-JUL",
            "RENT-AUG",
            "RENT-SEP",
        ),
        explanation="Estimated from six monthly records.",
    )


def test_forecast_becomes_forecast_obligation():
    obligations = forecasts_to_obligations(
        [make_forecast()]
    )

    assert len(obligations) == 1
    assert obligations[0].amount.amount == Decimal("100000")
    assert obligations[0].amount.currency == "XAF"
    assert obligations[0].due_date == date(2026, 10, 15)
    assert obligations[0].source == ObligationSource.FORECAST


def test_rejects_unexpected_source():
    with pytest.raises(ValueError, match="forecasts"):
        forecasts_to_obligations(
            [make_forecast(source="confirmed")]
        )


def test_empty_forecasts_produce_no_obligations():
    assert forecasts_to_obligations([]) == []
    
    
def test_assessment_calculates_surplus():
    forecasts = [
        ExpenseForecast(
            category="Office Bills",
            subcategory="Office rent",
            amount=Decimal("100000"),
            currency="XAF",
            due_date=date(2026, 10, 15),
            source="forecast",
            supporting_record_ids=("RENT-APR",),
            explanation="Development estimate.",
        )
    ]

    position = assess_forecast_liquidity(
        forecasts=forecasts,
        available_cash=Money(Decimal("500000"), "XAF"),
        minimum_buffer=Money(Decimal("200000"), "XAF"),
        planning_horizon=timedelta(days=30),
        as_of=date(2026, 10, 1),
    )

    assert position.deployable_surplus.amount == Decimal("200000")


def test_assessment_calculates_shortfall():
    forecasts = [
        ExpenseForecast(
            category="Office Bills",
            subcategory="Office rent",
            amount=Decimal("100000"),
            currency="XAF",
            due_date=date(2026, 10, 15),
            source="forecast",
            supporting_record_ids=("RENT-APR",),
            explanation="Development estimate.",
        )
    ]

    position = assess_forecast_liquidity(
        forecasts=forecasts,
        available_cash=Money(Decimal("250000"), "XAF"),
        minimum_buffer=Money(Decimal("200000"), "XAF"),
        planning_horizon=timedelta(days=30),
        as_of=date(2026, 10, 1),
    )

    assert position.liquidity_shortfall.amount == Decimal("50000")


def test_assessment_rejects_currency_mismatch():
    with pytest.raises(ValueError):
        assess_forecast_liquidity(
            forecasts=[make_forecast()],
            available_cash=Money(Decimal("500000"), "USD"),
            minimum_buffer=Money(Decimal("200000"), "USD"),
            planning_horizon=timedelta(days=30),
            as_of=date(2026, 10, 1),
        )