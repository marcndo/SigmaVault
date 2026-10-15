from datetime import datetime, timezone
from decimal import Decimal

from pydantic_ai import RunContext

from sigmavault.integrations.arc.wallet_snapshot import ArcWalletSnapshot
from sigmavault.treasury.treasury_agent import (
    TreasuryAgentContext,
    inspect_arc_wallet,
)


def make_context(snapshot=None):
    return TreasuryAgentContext(
        status="sufficient",
        deployable_surplus=Decimal("50000"),
        liquidity_shortfall=Decimal("0"),
        currency="XAF",
        evidence_verified=False,
        arc_wallet_snapshot=snapshot,
    )


def test_arc_wallet_tool_handles_missing_snapshot():
    ctx = RunContext(
        deps=make_context(),
        model=None,
        usage=None,
        prompt=None,
    )

    result = inspect_arc_wallet(ctx)

    assert result["available"] is False
    assert result["execution_authorized"] is False


def test_arc_wallet_tool_exposes_observed_balance():
    snapshot = ArcWalletSnapshot(
        address="0x0000000000000000000000000000000000000001",
        chain_id=5042002,
        block_number=12345,
        native_usdc_balance=Decimal("5"),
        observed_at=datetime(
            2026, 10, 15, tzinfo=timezone.utc
        ),
    )

    ctx = RunContext(
        deps=make_context(snapshot),
        model=None,
        usage=None,
        prompt=None,
    )

    result = inspect_arc_wallet(ctx)

    assert result["available"] is True
    assert result["chain_id"] == 5042002
    assert result["native_usdc_balance"] == "5"
    assert result["currency"] == "USDC"
    assert result["execution_authorized"] is False