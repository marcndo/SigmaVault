from sigmavault.treasury.domain import LiquidityPosition
from sigmavault.integrations.arc.wallet_snapshot import ArcWalletSnapshot
from sigmavault.treasury.treasury_agent import (
    TreasuryAgentContext,
    TreasuryRecommendation,
    treasury_agent,
)


def run_treasury_agent(
    position: LiquidityPosition,
    *,
    evidence_verified: bool = False,
    arc_wallet_snapshot: ArcWalletSnapshot | None = None,
    model=None,
) -> TreasuryRecommendation:
    """Run an advisory treasury agent without execution authority."""

    context = TreasuryAgentContext(
        status=position.status.value,
        deployable_surplus=position.deployable_surplus.amount,
        liquidity_shortfall=position.liquidity_shortfall.amount,
        currency=position.available_cash.currency,
        evidence_verified=evidence_verified,
        arc_wallet_snapshot=arc_wallet_snapshot,
    )

    result = treasury_agent.run_sync(
        "Inspect the treasury position and recommend the safest action.",
        deps=context,
        model=model,
    )

    recommendation = result.output

    # Independent deterministic safeguards.
    if (
        not evidence_verified
        or position.status.value == "insufficient"
        or position.liquidity_shortfall.amount > 0
    ):
        return TreasuryRecommendation(
            action="preserve_liquidity",
            explanation=(
                "Execution is not eligible because financial evidence "
                "is unverified or liquidity is insufficient. "
                "Human review is required."
            ),
            requires_human_review=True,
        )

    # A recommendation is not financial authorization.
    return TreasuryRecommendation(
        action="investigate",
        explanation=recommendation.explanation,
        requires_human_review=True,
    )