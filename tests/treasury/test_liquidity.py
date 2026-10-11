
from datetime import date, timedelta
from decimal import Decimal

import pytest

from sigmavault.treasury.domain import (
    LiquidityStatus,
    Money,
    Obligation,
    ObligationSource,
    TreasuryPolicy,
)
from sigmavault.treasury.liquidity import calculate_liquidity


AS_OF = date(2026, 10, 10)


def money(amount: str, currency: str = "USD") -> Money:
    """Create a Money object using exact decimal arithmetic."""
    return Money(
        amount=Decimal(amount),
        currency=currency,
    )


def obligation(
    amount: str,
    due_date: date,
    source: ObligationSource = ObligationSource.CONFIRMED,
) -> Obligation:
    """Create an outstanding obligation for testing."""
    return Obligation(
        amount = money(amount),
        due_date = due_date,
        source = source,
    )


def policy(buffer: str = "8000") -> TreasuryPolicy:
    """Create a standard 30-day treasury policy."""
    return TreasuryPolicy(
        planning_horizon = timedelta(days=30),
        minimum_cash_buffer = money(buffer),
    )


def test_cash_is_sufficient():
    available_cash = money("40000")

    obligations = [
        obligation("12000", date(2026, 10, 20)),
        obligation("10000", date(2026, 10, 30)),
    ]

    result = calculate_liquidity(
        available_cash = available_cash,
        obligations = obligations,
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.available_cash == money("40000")
    assert result.required_liquidity == money("22000")
    assert result.minimum_cash_buffer == money("8000")
    assert result.deployable_surplus == money("10000")
    assert result.liquidity_shortfall == money("0")
    assert result.status is LiquidityStatus.SUFFICIENT


def test_insufficient_cash():
    result = calculate_liquidity(
        available_cash=money("25000"),
        obligations=[
            obligation("22000", date(2026, 10, 20)),
        ],
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.required_liquidity == money("22000")
    assert result.deployable_surplus == money("0")
    assert result.liquidity_shortfall == money("5000")
    assert result.status is LiquidityStatus.INSUFFICIENT


def test_exact_liquidity_boundary():
    result = calculate_liquidity(
        available_cash = money("30000"),
        obligations=[
            obligation("22000", date(2026, 10, 20)),
        ],
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.required_liquidity == money("22000")
    assert result.deployable_surplus == money("0")
    assert result.liquidity_shortfall == money("0")
    assert result.status is LiquidityStatus.SUFFICIENT


def test_excludes_obligations_beyond_horizon():
    result = calculate_liquidity(
        available_cash = money("40000"),
        obligations = [
            obligation("12000", date(2026, 10, 20)),
            obligation("5000", date(2026, 11, 25)),
        ],
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.required_liquidity == money("12000")
    assert result.deployable_surplus == money("20000")


def test_includes_outstanding_overdue_obligations():
    result = calculate_liquidity(
        available_cash = money("40000"),
        obligations = [
            obligation("5000", date(2026, 10, 5)),
        ],
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.required_liquidity == money("5000")
    assert result.deployable_surplus == money("27000")


def test_includes_obligation_on_horizon_boundary():
    horizon_end = AS_OF + timedelta(days=30)

    result = calculate_liquidity(
        available_cash=money("40000"),
        obligations=[
            obligation("5000", horizon_end),
        ],
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.required_liquidity == money("5000")


def test_includes_forecast_obligations():
    forecast = obligation(
        amount = "6000",
        due_date = date(2026, 10, 25),
        source = ObligationSource.FORECAST,
    )

    result = calculate_liquidity(
        available_cash = money("40000"),
        obligations = [forecast],
        policy = policy(),
        as_of = AS_OF,
    )

    assert result.required_liquidity == money("6000")
    assert result.deployable_surplus == money("26000")


def test_no_obligations():
    result = calculate_liquidity(
        available_cash=money("40000"),
        obligations=[],
        policy=policy(),
        as_of=AS_OF,
    )

    assert result.required_liquidity == money("0")
    assert result.deployable_surplus == money("32000")
    assert result.liquidity_shortfall == money("0")
    assert result.status is LiquidityStatus.SUFFICIENT


def test_rejects_obligation_currency_mismatch():
    foreign_obligation = Obligation(
        amount = money("12000", "EUR"),
        due_date = date(2026, 10, 20),
        source = ObligationSource.CONFIRMED,
    )

    with pytest.raises(ValueError, match="currency"):
        calculate_liquidity(
            available_cash=money("40000"),
            obligations = [foreign_obligation],
            policy = policy(),
            as_of = AS_OF,
        )


def test_rejects_buffer_currency_mismatch():
    foreign_currency_policy = TreasuryPolicy(
        planning_horizon = timedelta(days=30),
        minimum_cash_buffer = money("8000", "EUR"),
    )

    with pytest.raises(ValueError, match="currency"):
        calculate_liquidity(
            available_cash = money("40000"),
            obligations = [],
            policy = foreign_currency_policy,
            as_of = AS_OF,
        )


def test_rejects_negative_available_cash():
    with pytest.raises(ValueError, match="negative"):
        calculate_liquidity(
            available_cash = money("-100"),
            obligations = [],
            policy = policy(),
            as_of = AS_OF,
        )


def test_rejects_negative_obligation():
    with pytest.raises(ValueError, match="negative"):
        calculate_liquidity(
            available_cash=money("40000"),
            obligations=[
                obligation("-500", date(2026, 10, 20)),
            ],
            policy = policy(),
            as_of = AS_OF,
        )
