from datetime import date
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)

from sigmavault.treasury.signed_decision_record import (
    create_signed_decision_record,
)
from sigmavault.treasury.signed_decision_record import SignedDecisionRecord
from sigmavault.treasury.signed_decision_audit import (
    DecisionAuditPayloadV2,
    hash_beancount_entry,
)


def test_signed_decision_record_stores_audit_artifacts():
    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" "DEC-001: approved"\n'
        '  decision_id: "DEC-001"\n'
        '  outcome: "approved"\n'
        '  explanation: "Reserve preserved."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(journal_entry),
    )

    signature = b"example-signature"

    record = SignedDecisionRecord(
        payload=payload,
        journal_entry=journal_entry,
        signature=signature,
    )

    assert record.payload == payload
    assert record.journal_entry == journal_entry
    assert record.signature == signature
    
def test_create_signed_decision_record_produces_verifiable_audit():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
    )

    event_date = date(2026, 10, 14)

    record = create_signed_decision_record(
        decision=decision,
        event_date=event_date,
        policy_version="1.0.0",
        private_key=private_key,
    )

    assert isinstance(record, SignedDecisionRecord)

    assert record.payload.decision_id == decision.decision_id
    assert record.payload.outcome == decision.outcome
    assert record.payload.explanation == decision.explanation
    assert record.payload.event_date == event_date
    assert record.payload.policy_version == "1.0.0"

    assert record.payload.journal_sha256 == hash_beancount_entry(
        record.journal_entry
    )

    assert verify_complete_decision_audit(
        payload=record.payload,
        journal_entry=record.journal_entry,
        signature=record.signature,
        public_key=public_key,
    ) is True
    
    
@pytest.mark.parametrize(
    ("outcome", "explanation"),
    [
        ("approved", "Liquidity safeguards are satisfied."),
        ("rejected", "Insufficient available liquidity."),
        ("deferred", "Settlement evidence is not yet available."),
    ],
)
def test_create_signed_decision_record_supports_all_outcomes(
    outcome: str,
    explanation: str,
):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome=outcome,
        explanation=explanation,
    )

    record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    assert record.payload.outcome == outcome
    assert record.payload.explanation == explanation

    assert verify_complete_decision_audit(
        payload=record.payload,
        journal_entry=record.journal_entry,
        signature=record.signature,
        public_key=public_key,
    ) is True
    
@pytest.mark.parametrize(
    "explanation",
    [
        'Policy "v1.0" approved.',
        r"Evidence path: C:\treasury\reports",
        "Liquidity reserve preserved.\nSettlement pending.",
        "Liquidity reserve preserved.\rSettlement pending.",
        'Policy "v1.0" approved.\nEvidence: C:\\treasury\\reports',
        "Réserve de liquidité préservée.",
    ],
)
def test_create_signed_decision_record_preserves_special_characters(
    explanation: str,
):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation=explanation,
    )

    record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        private_key=private_key,
    )

    # The structured audit payload preserves the original explanation.
    assert record.payload.explanation == explanation

    # The complete verifier must accept the generated journal.
    assert verify_complete_decision_audit(
        payload=record.payload,
        journal_entry=record.journal_entry,
        signature=record.signature,
        public_key=public_key,
    ) is True
    
@pytest.mark.parametrize(
    "policy_version",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
    ],
)
def test_create_signed_decision_record_rejects_blank_policy_version(
    policy_version: str,
):
    private_key = Ed25519PrivateKey.generate()

    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Liquidity safeguards are satisfied.",
    )

    with pytest.raises(ValueError):
        create_signed_decision_record(
            decision=decision,
            event_date=date(2026, 10, 14),
            policy_version=policy_version,
            private_key=private_key,
        )