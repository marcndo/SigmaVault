import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import Mock, patch
from dataclasses import replace

from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from pydantic_ai.models.test import TestModel

from sigmavault.integrations.arc.wallet_snapshot import ArcWalletSnapshot
from sigmavault.treasury.arc_forecast_workflow import (
    run_arc_forecast_workflow,
)
from sigmavault.treasury.decision_service import TreasuryDecisionService
from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def test_arc_forecast_decision_is_persisted():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteSignedDecisionRepository(connection)

    private_key = Ed25519PrivateKey.generate()

    decision_service = TreasuryDecisionService(
        repository=repository,
        private_key=private_key,
        policy_version="test-policy-v1",
    )

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
            decision_id="arc-persistence-test-001",
            decision_service=decision_service,
            arc_gateway=Mock(),
            wallet_address=snapshot.address,
            model=TestModel(),
        )

    # Commit explicitly: repository.save() does not own the transaction.
    connection.commit()

    stored_record = repository.get_by_decision_id(
        "arc-persistence-test-001"
    )

    assert stored_record is not None
    assert stored_record == result.signed_decision
    # The verification key is derived independently from the signing key.
    public_key = private_key.public_key()
    
    assert verify_complete_decision_audit(
        payload=stored_record.payload,
        journal_entry=stored_record.journal_entry,
        signature=stored_record.signature,
        public_key=public_key,
    ) is True
    assert result.recommendation.action == "preserve_liquidity"
    assert result.recommendation.requires_human_review is True
    # An altered journal must fail verification.
    tampered_journal = stored_record.journal_entry + "\n; tampered"
    
    assert verify_complete_decision_audit(
        payload=stored_record.payload,
        journal_entry=tampered_journal,
        signature=stored_record.signature,
        public_key=public_key,
    ) is False
    
    
    # An altered signature must fail verification.
    tampered_signature = bytearray(stored_record.signature)
    tampered_signature[0] ^= 0x01
    
    assert verify_complete_decision_audit(
        payload=stored_record.payload,
        journal_entry=stored_record.journal_entry,
        signature=bytes(tampered_signature),
        public_key=public_key,
    ) is False

    connection.close()