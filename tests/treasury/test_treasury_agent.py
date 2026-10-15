from decimal import Decimal

from pydantic_ai.models.test import TestModel

from sigmavault.treasury.agent_runner import run_treasury_agent
from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
)


def test_agent_cannot_authorize_unverified_funds():
    position = LiquidityPosition(
        available_cash=Money(Decimal("100000"), "XAF"),
        required_liquidity=Money(Decimal("25000"), "XAF"),
        minimum_cash_buffer=Money(Decimal("20000"), "XAF"),
        deployable_surplus=Money(Decimal("55000"), "XAF"),
        liquidity_shortfall=Money(Decimal("0"), "XAF"),
        status=LiquidityStatus.SUFFICIENT,
    )

    recommendation = run_treasury_agent(
        position,
        evidence_verified=False,
        model=TestModel(),
    )

    assert recommendation.action == "preserve_liquidity"
    assert recommendation.requires_human_review is True
    assert "unverified" in recommendation.explanation