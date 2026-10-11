from collections.abc import Sequence
from datetime import date, timedelta
from sigmavault.treasury.forecasting import ExpenseForecast
from sigmavault.treasury.liquidity import calculate_liquidity

from sigmavault.treasury.domain import (
    Money,
    Obligation,
    ObligationSource,
    LiquidityPosition,
    TreasuryPolicy,
)


def forecasts_to_obligations(
    forecasts: Sequence[ExpenseForecast],
) -> list[Obligation]:
    """Convert estimated expenses into forecast obligations."""

    obligations = []

    for forecast in forecasts:
        if forecast.source != "forecast":
            raise ValueError(
                "Only explicitly labeled forecasts are accepted"
            )

        if forecast.amount <= 0:
            raise ValueError(
                "Forecast amount must be positive"
            )

        obligations.append(
            Obligation(
                amount=Money(
                    amount=forecast.amount,
                    currency=forecast.currency,
                ),
                due_date=forecast.due_date,
                source=ObligationSource.FORECAST,
            )
        )

    return obligations


def assess_forecast_liquidity(
    forecasts: Sequence[ExpenseForecast],
    available_cash: Money,
    minimum_buffer: Money,
    planning_horizon: timedelta,
    as_of: date,
) -> LiquidityPosition:
    """
    Calculate liquidity using estimated financial obligations.

    This is an assessment, not authorization to execute
    any financial transaction.
    """
    obligations = forecasts_to_obligations(forecasts)

    policy = TreasuryPolicy(
        planning_horizon=planning_horizon,
        minimum_cash_buffer=minimum_buffer,
    )

    return calculate_liquidity(
        available_cash=available_cash,
        obligations=obligations,
        policy=policy,
        as_of=as_of,
    )