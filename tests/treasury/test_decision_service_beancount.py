import sqlite3
from datetime import date
from decimal import Decimal

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.beancount_audit_journal import (
    BeancountAuditJournal,
)
from sigmavault.treasury.decision_service import (
    TreasuryDecisionService,
)
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


def test_decision_service_writes_signed_beancount_event(tmp_path):
    """A treasury assessment writes a signed journal event and DB record."""

    database_path = tmp_path / "treasury.sqlite3"
    journal_path = tmp_path / "treasury_decisions.beancount"

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

    journal = BeancountAuditJournal(
        path=journal_path,
        public_key=public_key,
    )

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        service = TreasuryDecisionService(
            repository=repository,
            private_key=private_key,
            policy_version="pilot-v1",
            journal=journal,
        )

        created_record = service.assess_and_record(
            decision_id="DEC-BEANCOUNT-001",
            position=position,
            event_date=date(2026, 10, 15),
        )

        connection.commit()

    finally:
        connection.close()

    # Verify that the actual Beancount file exists.
    assert journal_path.exists()

    journal_content = journal_path.read_text(
        encoding="utf-8",
    )

    # Verify that the exact signed event was appended.
    assert created_record.journal_entry in journal_content

    assert "SigmaVaultDecision" in journal_content
    assert "DEC-BEANCOUNT-001" in journal_content
    assert "deferred" in journal_content

    # Verify that the decision explanation appears in the file.
    assert created_record.payload.explanation in journal_content

    # Retrieve the signed record from a fresh database connection.
    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        stored_record = repository.get_by_decision_id(
            "DEC-BEANCOUNT-001"
        )

    finally:
        connection.close()

    assert stored_record is not None
    assert stored_record == created_record

    # Verify signature, journal hash, and Beancount semantics.
    assert verify_complete_decision_audit(
        payload=stored_record.payload,
        journal_entry=stored_record.journal_entry,
        signature=stored_record.signature,
        public_key=public_key,
    ) is True