from dataclasses import dataclass
from datetime import date, timedelta

from sigmavault.integrations.arc.gateway import ArcGateway
from sigmavault.integrations.arc.wallet_snapshot import (
    ArcWalletSnapshot,
    capture_arc_wallet_snapshot,
)
from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.integrations.firefly.forecast_service import (
    generate_firefly_expense_forecasts,
)
from sigmavault.treasury.agent_runner import run_treasury_agent
from sigmavault.treasury.assessment import assess_forecast_liquidity
from sigmavault.treasury.decision_service import TreasuryDecisionService
from sigmavault.treasury.domain import LiquidityPosition, Money
from sigmavault.treasury.signed_decision_record import SignedDecisionRecord
from sigmavault.treasury.treasury_agent import TreasuryRecommendation


@dataclass(frozen=True)
class ArcForecastWorkflowResult:
    liquidity_position: LiquidityPosition
    wallet_snapshot: ArcWalletSnapshot
    recommendation: TreasuryRecommendation
    signed_decision: SignedDecisionRecord


def run_arc_forecast_workflow(
    *,
    client: FireflyClient,
    account_id: int,
    as_of: date,
    available_cash: Money,
    minimum_buffer: Money,
    planning_horizon: timedelta,
    decision_id: str,
    decision_service: TreasuryDecisionService,
    arc_gateway: ArcGateway,
    wallet_address: str,
    months_required: int = 6,
    model=None,
) -> ArcForecastWorkflowResult:
    """Analyze forecasts and Arc state without authorizing execution."""

    if available_cash.currency != "XAF":
        raise ValueError("Expected XAF-denominated available cash")

    if minimum_buffer.currency != "XAF":
        raise ValueError("Expected XAF-denominated minimum buffer")

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

    # This is a blockchain observation, not proof of business ownership
    # or permission to spend.
    snapshot = capture_arc_wallet_snapshot(
        gateway=arc_gateway,
        address=wallet_address,
    )

    # Record the deterministic decision before requesting AI advice.
    # An LLM failure must not change the policy decision.
    signed_decision = decision_service.assess_and_record(
        decision_id=decision_id,
        position=position,
        event_date=as_of,
    )

    recommendation = run_treasury_agent(
        position,
        evidence_verified=False,
        arc_wallet_snapshot=snapshot,
        model=model,
    )

    return ArcForecastWorkflowResult(
        liquidity_position=position,
        wallet_snapshot=snapshot,
        recommendation=recommendation,
        signed_decision=signed_decision,
    )