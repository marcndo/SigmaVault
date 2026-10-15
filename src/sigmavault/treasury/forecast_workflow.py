from datetime import date, timedelta

from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.integrations.firefly.forecast_service import (
    generate_firefly_expense_forecasts,
)
from sigmavault.treasury.assessment import assess_forecast_liquidity
from sigmavault.treasury.decision_service import TreasuryDecisionService
from sigmavault.treasury.domain import Money
from sigmavault.treasury.signed_decision_record import SignedDecisionRecord


def run_forecast_decision_workflow(
    client: FireflyClient,
    account_id: int,
    as_of: date,
    available_cash: Money,
    minimum_buffer: Money,
    planning_horizon: timedelta,
    decision_id: str,
    decision_service: TreasuryDecisionService,
    months_required: int = 6,
) -> SignedDecisionRecord:
    """Create a signed, non-executable forecast assessment."""

    forecasts = generate_firefly_expense_forecasts(
        client=client,
        account_id=account_id,
        as_of=as_of,
        months_required=months_required,
    )

    position = assess_forecast_liquidity(
        forecasts=forecasts,
        available_cash=available_cash,
        minimum_buffer=minimum_buffer,
        planning_horizon=planning_horizon,
        as_of=as_of,
    )

    return decision_service.assess_and_record(
        decision_id=decision_id,
        position=position,
        event_date=as_of,
    )