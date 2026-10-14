import sqlite3
from datetime import date
import pytest

from sigmavault.treasury.signed_decision_repository import (
    SignedDecisionRepository,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.signed_decision_record import (
    create_signed_decision_record,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
        hash_beancount_entry,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)

def test_signed_decision_repository_defines_required_operations():
    assert hasattr(SignedDecisionRepository, "save")
    assert hasattr(SignedDecisionRepository, "get_by_decision_id")
    

def test_sqlite_repository_persists_record_across_connections(tmp_path):
    database_path = tmp_path / "signed_decisions.sqlite3"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Liquidity safeguards are satisfied.",
    )

    original_record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    # First connection: persist the record.
    with sqlite3.connect(database_path) as connection:
        repository = SQLiteSignedDecisionRepository(connection)
        repository.save(original_record)
        connection.commit()

    # Second connection: retrieve the record.
    with sqlite3.connect(database_path) as connection:
        repository = SQLiteSignedDecisionRepository(connection)

        retrieved_record = repository.get_by_decision_id("DEC-001")

    assert retrieved_record is not None

    # All signed artifacts must survive storage and retrieval.
    assert retrieved_record == original_record

    # The retrieved record must remain independently verifiable.
    assert verify_complete_decision_audit(
        payload=retrieved_record.payload,
        journal_entry=retrieved_record.journal_entry,
        signature=retrieved_record.signature,
        public_key=public_key,
    ) is True
    
    
def test_sqlite_repository_returns_none_for_missing_decision(tmp_path):
    database_path = tmp_path / "signed_decisions.sqlite3"

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        result = repository.get_by_decision_id("DEC-DOES-NOT-EXIST")

        assert result is None

    finally:
        connection.close()
        
def test_sqlite_repository_rejects_duplicate_decision_id(tmp_path):
    database_path = tmp_path / "signed_decisions.sqlite3"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    original_decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Liquidity safeguards are satisfied.",
    )

    conflicting_decision = AgentDecision(
        decision_id="DEC-001",
        outcome="rejected",
        explanation="Insufficient available liquidity.",
    )

    original_record = create_signed_decision_record(
        decision=original_decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    conflicting_record = create_signed_decision_record(
        decision=conflicting_decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        # Store and commit the original record.
        repository.save(original_record)
        connection.commit()

        # A conflicting record with the same ID must be rejected.
        with pytest.raises(sqlite3.IntegrityError):
            repository.save(conflicting_record)

        connection.rollback()

        # The original signed record must remain unchanged.
        stored_record = repository.get_by_decision_id("DEC-001")

        assert stored_record == original_record
        assert stored_record != conflicting_record

        assert verify_complete_decision_audit(
            payload=stored_record.payload,
            journal_entry=stored_record.journal_entry,
            signature=stored_record.signature,
            public_key=public_key,
        ) is True

    finally:
        connection.close()
        
        
def test_sqlite_repository_rollback_discards_uncommitted_record(tmp_path):
    database_path = tmp_path / "signed_decisions.sqlite3"

    private_key = Ed25519PrivateKey.generate()

    decision = AgentDecision(
        decision_id="DEC-ROLLBACK-001",
        outcome="deferred",
        explanation="Settlement evidence is not yet available.",
    )

    record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    # First connection: save the record without committing.
    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        repository.save(record)

        # The current connection can see its uncommitted write.
        assert repository.get_by_decision_id(
            "DEC-ROLLBACK-001"
        ) == record

        # The caller decides to cancel the transaction.
        connection.rollback()

        assert repository.get_by_decision_id(
            "DEC-ROLLBACK-001"
        ) is None

    finally:
        connection.close()

    # Second connection: verify the record was not persisted.
    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        assert repository.get_by_decision_id(
            "DEC-ROLLBACK-001"
        ) is None

    finally:
        connection.close()
        
def test_sqlite_repository_retrieves_but_does_not_trust_tampered_record(
    tmp_path,
):
    database_path = tmp_path / "signed_decisions.sqlite3"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Liquidity safeguards are satisfied.",
    )

    original_record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        repository.save(original_record)
        connection.commit()

        # Confirm the original record is authentic.
        assert verify_complete_decision_audit(
            payload=original_record.payload,
            journal_entry=original_record.journal_entry,
            signature=original_record.signature,
            public_key=public_key,
        ) is True

        # Simulate unauthorized modification of the database.
        connection.execute(
            """
            UPDATE signed_decision_records
            SET outcome = ?
            WHERE decision_id = ?
            """,
            ("rejected", "DEC-001"),
        )
        connection.commit()

    finally:
        connection.close()

    # Retrieve the modified record through a new connection.
    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        retrieved_record = repository.get_by_decision_id("DEC-001")

    finally:
        connection.close()

    # The database still returns a structurally valid record.
    assert retrieved_record is not None
    assert retrieved_record.payload.outcome == "rejected"

    # But the original signature does not authenticate the modified payload.
    assert verify_complete_decision_audit(
        payload=retrieved_record.payload,
        journal_entry=retrieved_record.journal_entry,
        signature=retrieved_record.signature,
        public_key=public_key,
    ) is False
    
    
def test_sqlite_repository_detects_tampered_journal_entry(tmp_path):
    database_path = tmp_path / "signed_decisions.sqlite3"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Liquidity safeguards are satisfied.",
    )

    original_record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    tampered_journal = original_record.journal_entry.replace(
        "Liquidity safeguards are satisfied.",
        "Liquidity safeguards have failed.",
    )

    assert tampered_journal != original_record.journal_entry

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        repository.save(original_record)
        connection.commit()

        # Simulate unauthorized modification of the stored journal.
        connection.execute(
            """
            UPDATE signed_decision_records
            SET journal_entry = ?
            WHERE decision_id = ?
            """,
            (tampered_journal, "DEC-001"),
        )
        connection.commit()

    finally:
        connection.close()

    # Retrieve the modified record using a fresh connection.
    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)
        retrieved_record = repository.get_by_decision_id("DEC-001")

    finally:
        connection.close()

    assert retrieved_record is not None

    # The repository preserves the modified database contents.
    assert retrieved_record.journal_entry == tampered_journal

    # The signed payload remains unchanged.
    assert retrieved_record.payload == original_record.payload
    assert retrieved_record.signature == original_record.signature

    # The modified journal no longer matches the signed digest.
    assert (
        hash_beancount_entry(retrieved_record.journal_entry)
        != retrieved_record.payload.journal_sha256
    )

    assert verify_complete_decision_audit(
        payload=retrieved_record.payload,
        journal_entry=retrieved_record.journal_entry,
        signature=retrieved_record.signature,
        public_key=public_key,
    ) is False
    
    
def test_sqlite_repository_detects_tampered_signature(tmp_path):
    database_path = tmp_path / "signed_decisions.sqlite3"

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-SIGNATURE-001",
        outcome="approved",
        explanation="Liquidity safeguards are satisfied.",
    )

    original_record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    # Modify one byte while preserving the signature's length.
    tampered_signature = (
        bytes([original_record.signature[0] ^ 0x01])
        + original_record.signature[1:]
    )

    assert tampered_signature != original_record.signature
    assert len(tampered_signature) == len(original_record.signature)

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        repository.save(original_record)
        connection.commit()

        # Confirm that the original record is authentic.
        assert verify_complete_decision_audit(
            payload=original_record.payload,
            journal_entry=original_record.journal_entry,
            signature=original_record.signature,
            public_key=public_key,
        ) is True

        # Simulate unauthorized modification of the signature.
        connection.execute(
            """
            UPDATE signed_decision_records
            SET signature = ?
            WHERE decision_id = ?
            """,
            (tampered_signature, "DEC-SIGNATURE-001"),
        )
        connection.commit()

    finally:
        connection.close()

    # Retrieve the modified record through a fresh connection.
    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        retrieved_record = repository.get_by_decision_id(
            "DEC-SIGNATURE-001"
        )

    finally:
        connection.close()

    assert retrieved_record is not None

    # The payload and journal remain unchanged.
    assert retrieved_record.payload == original_record.payload
    assert retrieved_record.journal_entry == original_record.journal_entry

    # Only the signature was modified.
    assert retrieved_record.signature == tampered_signature

    # Cryptographic verification must reject the modified signature.
    assert verify_complete_decision_audit(
        payload=retrieved_record.payload,
        journal_entry=retrieved_record.journal_entry,
        signature=retrieved_record.signature,
        public_key=public_key,
    ) is False