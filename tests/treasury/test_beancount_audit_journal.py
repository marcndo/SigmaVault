from dataclasses import replace
from datetime import date

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.beancount_audit_journal import (
    BeancountAuditJournal,
)
from sigmavault.treasury.signed_decision_record import (
    create_signed_decision_record,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)


@pytest.fixture
def signed_record_and_key():
    """Create a valid signed treasury decision and its public key."""

    private_key = Ed25519PrivateKey.generate()

    decision = AgentDecision(
        decision_id="decision-001",
        outcome="deferred",
        explanation="Preserve liquidity pending financial verification.",
    )

    record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 15),
        policy_version="pilot-v1",
        private_key=private_key,
    )

    return record, private_key.public_key()


def test_append_creates_beancount_file(
    tmp_path,
    signed_record_and_key,
):
    """A valid signed decision creates a readable Beancount journal."""

    record, public_key = signed_record_and_key

    journal_path = tmp_path / "treasury_decisions.beancount"

    journal = BeancountAuditJournal(
        journal_path,
        public_key,
    )

    journal.append(record)

    assert journal_path.exists()

    content = journal_path.read_text(encoding="utf-8")

    assert "SigmaVaultDecision" in content
    assert "decision-001" in content
    assert "deferred" in content
    assert record.payload.explanation in content

    assert verify_complete_decision_audit(
        payload=record.payload,
        journal_entry=record.journal_entry,
        signature=record.signature,
        public_key=public_key,
    )


def test_append_preserves_existing_entries(
    tmp_path,
    signed_record_and_key,
):
    """Reject an inconsistent decision without changing existing entries."""

    record, public_key = signed_record_and_key

    journal_path = tmp_path / "treasury_decisions.beancount"

    journal = BeancountAuditJournal(
        journal_path,
        public_key,
    )

    journal.append(record)

    original_content = journal_path.read_text(encoding="utf-8")

    # Change the decision ID without regenerating the journal
    # or its digital signature.
    tampered_record = replace(
        record,
        payload=replace(
            record.payload,
            decision_id="decision-002",
        ),
    )

    with pytest.raises(
        ValueError,
        match="Signed decision audit verification failed",
    ):
        journal.append(tampered_record)

    assert journal_path.read_text(encoding="utf-8") == original_content


def test_append_rejects_tampered_journal(
    tmp_path,
    signed_record_and_key,
):
    """Reject a modified explanation that invalidates the journal hash."""

    record, public_key = signed_record_and_key

    journal_path = tmp_path / "treasury_decisions.beancount"

    tampered_record = replace(
        record,
        journal_entry=record.journal_entry.replace(
            "Preserve liquidity",
            "Transfer all funds",
        ),
    )

    journal = BeancountAuditJournal(
        journal_path,
        public_key,
    )

    with pytest.raises(
        ValueError,
        match="Signed decision audit verification failed",
    ):
        journal.append(tampered_record)

    assert not journal_path.exists()


def test_append_multiple_valid_decisions(
    tmp_path,
):
    """Append two independently signed decisions without overwriting."""

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    journal_path = tmp_path / "treasury_decisions.beancount"

    journal = BeancountAuditJournal(
        journal_path,
        public_key,
    )

    first_decision = AgentDecision(
        decision_id="decision-001",
        outcome="deferred",
        explanation="Preserve liquidity pending verification.",
    )

    second_decision = AgentDecision(
        decision_id="decision-002",
        outcome="rejected",
        explanation="Insufficient liquidity for the proposed allocation.",
    )

    first_record = create_signed_decision_record(
        decision=first_decision,
        event_date=date(2026, 10, 15),
        policy_version="pilot-v1",
        private_key=private_key,
    )

    second_record = create_signed_decision_record(
        decision=second_decision,
        event_date=date(2026, 10, 15),
        policy_version="pilot-v1",
        private_key=private_key,
    )

    journal.append(first_record)
    journal.append(second_record)

    content = journal_path.read_text(encoding="utf-8")

    assert content.count("SigmaVaultDecision") == 2

    assert "decision-001" in content
    assert "decision-002" in content

    assert first_record.payload.explanation in content
    assert second_record.payload.explanation in content

    assert content.index("decision-001") < content.index("decision-002")


def test_append_rejects_unauthorized_signing_key(
    tmp_path,
):
    """Reject a decision signed by a key other than the authorized key."""

    authorized_key = Ed25519PrivateKey.generate()
    unauthorized_key = Ed25519PrivateKey.generate()

    decision = AgentDecision(
        decision_id="decision-unauthorized",
        outcome="deferred",
        explanation="Attempted unauthorized audit entry.",
    )

    record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 15),
        policy_version="pilot-v1",
        private_key=unauthorized_key,
    )

    journal_path = tmp_path / "treasury_decisions.beancount"

    journal = BeancountAuditJournal(
        journal_path,
        authorized_key.public_key(),
    )

    with pytest.raises(
        ValueError,
        match="Signed decision audit verification failed",
    ):
        journal.append(record)

    assert not journal_path.exists()