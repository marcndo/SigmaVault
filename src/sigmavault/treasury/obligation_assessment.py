from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sigmavault.treasury.assessment import forecasts_to_obligations
from sigmavault.treasury.domain import (
    LiquidityPosition,
    Money,
    Obligation,
    ObligationSource,
    TreasuryPolicy,
)
from sigmavault.treasury.forecasting import ExpenseForecast
from sigmavault.treasury.liquidity import calculate_liquidity
from sigmavault.treasury.upcoming_obligations import UpcomingBill


@dataclass(frozen=True)
class ObligationAssessment:
    position: LiquidityPosition
    obligations_count: int
    forecasts_count: int
    forecast_coverage_available: bool
    requires_human_review: bool


def assess_upcoming_obligations(
    *,
    bills: Sequence[UpcomingBill],
    forecasts: Sequence[ExpenseForecast],
    available_cash: Money,
    minimum_buffer: Money,
    planning_horizon: timedelta,
    as_of: date,
) -> ObligationAssessment:
    """
    Produce an advisory liquidity assessment.

    Bills are explicit future obligations or estimates.
    Historical forecasts supplement bills only where no
    matching bill already exists.
    """

    horizon_end = as_of + planning_horizon

    relevant_bills = [
        bill
        for bill in bills
        if as_of <= bill.due_date <= horizon_end
    ]

    # Fail closed on duplicate bill identifiers.
    bill_ids = [bill.bill_id for bill in bills]

    if len(bill_ids) != len(set(bill_ids)):
        raise ValueError("Duplicate upcoming bill ID")

    obligations: list[Obligation] = []

    for bill in relevant_bills:
        obligations.append(
            Obligation(
                amount=bill.amount,
                due_date=bill.due_date,
                source=(
                    ObligationSource.CONFIRMED
                    if bill.status == "confirmed"
                    else ObligationSource.FORECAST
                ),
            )
        )

    # A forecast and an explicit bill may describe the same
    # financial obligation. Do not automatically sum both.
    #
    # We cannot reliably reconcile them using the current
    # Obligation domain model, which has no category or
    # external reference fields.
    #
    # Conservative policy: where explicit bills exist, do
    # not add historical forecasts automatically.
    if not relevant_bills:
        obligations.extend(forecasts_to_obligations(forecasts))

    policy = TreasuryPolicy(
        planning_horizon=planning_horizon,
        minimum_cash_buffer=minimum_buffer,
    )

    position = calculate_liquidity(
        available_cash=available_cash,
        obligations=obligations,
        policy=policy,
        as_of=as_of,
    )

    return ObligationAssessment(
        position=position,
        obligations_count=len(obligations),
        forecasts_count=len(forecasts),
        forecast_coverage_available=bool(forecasts),
        requires_human_review=True,
    )