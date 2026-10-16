import os
from decimal import Decimal

from pydantic_ai.models.test import TestModel

from sigmavault.integrations.arc.gateway import ArcGateway
from sigmavault.integrations.arc.wallet_snapshot import (
    capture_arc_wallet_snapshot,
)
from sigmavault.treasury.agent_runner import run_treasury_agent
from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
)


def main():
    gateway = ArcGateway(os.environ["ARC_RPC_URL"])

    snapshot = capture_arc_wallet_snapshot(
        gateway,
        os.environ["ARC_WALLET_ADDRESS"],
    )

    # Demonstration data only; not verified OBSECT cash.
    position = LiquidityPosition(
        available_cash=Money(Decimal("100000"), "XAF"),
        required_liquidity=Money(Decimal("40000"), "XAF"),
        minimum_cash_buffer=Money(Decimal("20000"), "XAF"),
        deployable_surplus=Money(Decimal("40000"), "XAF"),
        liquidity_shortfall=Money(Decimal("0"), "XAF"),
        status=LiquidityStatus.SUFFICIENT,
    )

    recommendation = run_treasury_agent(
        position,
        evidence_verified=False,
        arc_wallet_snapshot=snapshot,
        model=TestModel(),
    )

    print("=== SIGMAVAULT ARC AGENT DEMO ===")
    print("Arc chain:", snapshot.chain_id)
    print("Observed block:", snapshot.block_number)
    print("Observed USDC:", snapshot.native_usdc_balance)
    print("XAF position:", "SYNTHETIC DEMO DATA")
    print("Recommendation:", recommendation.action)
    print("Explanation:", recommendation.explanation)
    print("Human review required:", recommendation.requires_human_review)


if __name__ == "__main__":
    main()