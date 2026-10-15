from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

from pydantic_ai.models.test import TestModel

from sigmavault.integrations.arc.wallet_snapshot import ArcWalletSnapshot
from sigmavault.treasury.arc_forecast_workflow import (
    run_arc_forecast_workflow,
)
from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
)


def test_arc_forecast_workflow_records_deferred_decision():
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

    decision_service = Mock()
    signed_record = Mock()
    decision_service.assess_and_record.return_value = signed_record

    with (
        patch(
            "sigmavault.treasury.arc_forecast_workflow."
            "generate_firefly_expense_forecasts",
            return_value=[],
        ),
        patch(
            "sigmavault.treasury.arc_forecast_workflow."
            "assess_forecast_liquidity",
            return_value=position,
        ),
        patch(
            "sigmavault.treasury.arc_forecast_workflow."
            "capture_arc_wallet_snapshot",
            return_value=snapshot,
        ),
    ):
        result = run_arc_forecast_workflow(
            client=Mock(),
            account_id=1,
            as_of=date(2026, 10, 15),
            available_cash=Money(Decimal("100000"), "XAF"),
            minimum_buffer=Money(Decimal("20000"), "XAF"),
            planning_horizon=timedelta(days=30),
            decision_id="arc-forecast-test-001",
            decision_service=decision_service,
            arc_gateway=Mock(),
            wallet_address=snapshot.address,
            model=TestModel(),
        )

    assert result.liquidity_position == position
    assert result.wallet_snapshot == snapshot
    assert result.signed_decision is signed_record

    assert result.recommendation.action == "preserve_liquidity"
    assert result.recommendation.requires_human_review is True

    decision_service.assess_and_record.assert_called_once_with(
        decision_id="arc-forecast-test-001",
        position=position,
        event_date=date(2026, 10, 15),
    )