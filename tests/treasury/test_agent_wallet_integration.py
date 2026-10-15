from datetime import datetime, timezone
from decimal import Decimal

from pydantic_ai.models.test import TestModel

from sigmavault.integrations.arc.wallet_snapshot import ArcWalletSnapshot
from sigmavault.treasury.agent_runner import run_treasury_agent
from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
)


def test_agent_preserves_liquidity_with_arc_wallet():
    position = LiquidityPosition(
        available_cash=Money(Decimal("100000"), "XAF"),
        required_liquidity=Money(Decimal("40000"), "XAF"),
        minimum_cash_buffer=Money(Decimal("20000"), "XAF"),
        deployable_surplus=Money(Decimal("40000"), "XAF"),
        liquidity_shortfall=Money(Decimal("0"), "XAF"),
        status=LiquidityStatus.SUFFICIENT,
    )

    snapshot = ArcWalletSnapshot(
        address="0x0000000000000000000000000000000000000001",
        chain_id=5042002,
        block_number=12345,
        native_usdc_balance=Decimal("5"),
        observed_at=datetime(2026, 10, 15, tzinfo=timezone.utc),
    )

    recommendation = run_treasury_agent(
        position,
        evidence_verified=False,
        arc_wallet_snapshot=snapshot,
        model=TestModel(),
    )

    assert recommendation.action == "preserve_liquidity"
    assert recommendation.requires_human_review is True