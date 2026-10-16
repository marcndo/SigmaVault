import sqlite3
from datetime import date

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.journal_synchronizer import (
    synchronize_journal,
)
from sigmavault.treasury.signed_decision_record import (
    create_signed_decision_record,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def test_rebuilds_missing_journal_from_signed_records(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    connection = sqlite3.connect(tmp_path / "audit.sqlite3")
    journal_path = tmp_path / "audit.beancount"

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        record = create_signed_decision_record(
            decision=AgentDecision(
                decision_id="TEST-001",
                outcome="deferred",
                explanation="Human review required.",
            ),
            event_date=date(2026, 10, 15),
            policy_version="pilot-v1",
            private_key=private_key,
        )

        repository.save(record)
        connection.commit()

        count = synchronize_journal(
            connection=connection,
            journal_path=journal_path,
            public_key=public_key,
        )

        assert count == 1
        assert record.journal_entry in journal_path.read_text()

        # Repeated synchronization must not duplicate events.
        assert synchronize_journal(
            connection=connection,
            journal_path=journal_path,
            public_key=public_key,
        ) == 1

    finally:
        connection.close()
        
        
def test_extends_existing_journal_with_new_committed_record(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    connection = sqlite3.connect(tmp_path / "audit.sqlite3")
    journal_path = tmp_path / "audit.beancount"

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        first = create_signed_decision_record(
            decision=AgentDecision(
                decision_id="TEST-001",
                outcome="deferred",
                explanation="First decision.",
            ),
            event_date=date(2026, 10, 15),
            policy_version="pilot-v1",
            private_key=private_key,
        )

        repository.save(first)
        connection.commit()

        assert synchronize_journal(
            connection, journal_path, public_key
        ) == 1

        second = create_signed_decision_record(
            decision=AgentDecision(
                decision_id="TEST-002",
                outcome="deferred",
                explanation="Second decision.",
            ),
            event_date=date(2026, 10, 15),
            policy_version="pilot-v1",
            private_key=private_key,
        )

        repository.save(second)
        connection.commit()

        assert synchronize_journal(
            connection, journal_path, public_key
        ) == 2

        content = journal_path.read_text(encoding="utf-8")

        assert content.count("SigmaVaultDecision") == 2
        assert "TEST-001" in content
        assert "TEST-002" in content

        # A retry must not duplicate either decision.
        assert synchronize_journal(
            connection, journal_path, public_key
        ) == 2

        assert journal_path.read_text(encoding="utf-8") == content

    finally:
        connection.close()
        
        
def test_rejects_tampered_existing_journal(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    connection = sqlite3.connect(tmp_path / "audit.sqlite3")
    journal_path = tmp_path / "audit.beancount"

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        record = create_signed_decision_record(
            decision=AgentDecision(
                decision_id="TEST-TAMPER-001",
                outcome="deferred",
                explanation="Human review required.",
            ),
            event_date=date(2026, 10, 15),
            policy_version="pilot-v1",
            private_key=private_key,
        )

        repository.save(record)
        connection.commit()

        synchronize_journal(
            connection, journal_path, public_key
        )

        original = journal_path.read_text(encoding="utf-8")
        tampered = original.replace(
            "Human review required.",
            "Automatically approved.",
        )

        assert tampered != original

        journal_path.write_text(tampered, encoding="utf-8")

        import pytest

        with pytest.raises(RuntimeError, match="valid signed record prefix"):
            synchronize_journal(
                connection, journal_path, public_key
            )

        assert journal_path.read_text(encoding="utf-8") == tampered

    finally:
        connection.close()