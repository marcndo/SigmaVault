import sqlite3
from datetime import date
from decimal import Decimal

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.decision_service import TreasuryDecisionService
from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def test_treasury_assessment_creates_persistent_verified_audit(tmp_path):
    database_path = tmp_path / "treasury.sqlite3"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    position = LiquidityPosition(
        available_cash=Money(Decimal("1000000"), "XAF"),
        required_liquidity=Money(Decimal("400000"), "XAF"),
        minimum_cash_buffer=Money(Decimal("200000"), "XAF"),
        deployable_surplus=Money(Decimal("400000"), "XAF"),
        liquidity_shortfall=Money(Decimal("0"), "XAF"),
        status=LiquidityStatus.SUFFICIENT,
    )

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        service = TreasuryDecisionService(
            repository=repository,
            private_key=private_key,
            policy_version="1.0.0",
        )

        created_record = service.assess_and_record(
            decision_id="DEC-INTEGRATION-001",
            position=position,
            event_date=date(2026, 10, 14),
        )

        connection.commit()

    finally:
        connection.close()

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        stored_record = repository.get_by_decision_id(
            "DEC-INTEGRATION-001"
        )

    finally:
        connection.close()

    assert stored_record == created_record
    assert stored_record.payload.outcome == "deferred"
    assert "400000 XAF" in stored_record.payload.explanation

    assert verify_complete_decision_audit(
        payload=stored_record.payload,
        journal_entry=stored_record.journal_entry,
        signature=stored_record.signature,
        public_key=public_key,
    ) is True