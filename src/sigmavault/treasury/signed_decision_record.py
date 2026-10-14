from dataclasses import dataclass
from datetime import date

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.beancount_decision_journal import (
    render_decision_event,
)
from sigmavault.treasury.signed_decision_audit import (
    DecisionAuditPayloadV2,
    hash_beancount_entry,
    sign_audit_payload_v2,
)


@dataclass(frozen=True)
class SignedDecisionRecord:
    """Immutable container for a signed treasury decision audit."""

    payload: DecisionAuditPayloadV2
    journal_entry: str
    signature: bytes


def create_signed_decision_record(
    decision: AgentDecision,
    event_date: date,
    policy_version: str,
    private_key: Ed25519PrivateKey,
) -> SignedDecisionRecord:
    """Create a signed audit record for a treasury decision."""

    journal_entry = render_decision_event(
        decision=decision,
        event_date=event_date,
    )

    journal_sha256 = hash_beancount_entry(journal_entry)

    payload = DecisionAuditPayloadV2(
        decision_id=decision.decision_id,
        outcome=decision.outcome,
        explanation=decision.explanation,
        event_date=event_date,
        policy_version=policy_version,
        journal_sha256=journal_sha256,
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=private_key,
    )

    return SignedDecisionRecord(
        payload=payload,
        journal_entry=journal_entry,
        signature=signature,
    )