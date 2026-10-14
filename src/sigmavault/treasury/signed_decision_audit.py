from dataclasses import dataclass
from datetime import date
import json
import hashlib
from beancount.loader import load_string
from beancount.core.data import Event
from sigmavault.treasury.agent_decision import ALLOWED_OUTCOMES
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

AUDIT_SCHEMA_VERSION = 1

@dataclass(frozen=True)
class DecisionAuditPayload:
    """Represent the information associated with a treasury decision."""

    decision_id: str
    outcome: str
    explanation: str
    event_date: date
    policy_version: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.decision_id, str)
            or not self.decision_id.strip()
        ):
            raise ValueError("Decision audit ID must not be blank")

        if (
            not isinstance(self.outcome, str)
            or self.outcome not in ALLOWED_OUTCOMES
        ):
            raise ValueError("Invalid decision audit outcome")

        if (
            not isinstance(self.explanation, str)
            or not self.explanation.strip()
        ):
            raise ValueError(
                "Decision audit explanation must not be blank"
            )

        if type(self.event_date) is not date:
            raise ValueError(
                "Decision audit event date must be a date"
            )

        if (
            not isinstance(self.policy_version, str)
            or not self.policy_version.strip()
        ):
            raise ValueError(
                "Decision audit policy version must not be blank"
            )
   
            
@dataclass(frozen=True)
class DecisionAuditPayloadV2:
    """Represent a treasury decision bound to a Beancount journal digest."""

    decision_id: str
    outcome: str
    explanation: str
    event_date: date
    policy_version: str
    journal_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise ValueError("Decision audit ID must not be blank")

        if not isinstance(self.outcome, str) or self.outcome not in ALLOWED_OUTCOMES:
            raise ValueError("Invalid decision audit outcome")

        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("Decision audit explanation must not be blank")

        if type(self.event_date) is not date:
            raise ValueError("Decision audit event date must be a date")

        if not isinstance(self.policy_version, str) or not self.policy_version.strip():
            raise ValueError("Decision audit policy version must not be blank")

        if (
            not isinstance(self.journal_sha256, str)
            or len(self.journal_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.journal_sha256)
        ):
            raise ValueError(
                "Decision audit journal digest must be a 64-character lowercase SHA-256 hex string"
            )
            
def serialize_audit_payload(payload: DecisionAuditPayload) -> bytes:
    """Serialize an audit payload into deterministic UTF-8 JSON bytes."""
    data = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "decision_id": payload.decision_id,
        "outcome": payload.outcome,
        "explanation": payload.explanation,
        "event_date": payload.event_date.isoformat(),
        "policy_version": payload.policy_version,
    }

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    
def serialize_audit_payload_v2(payload: DecisionAuditPayloadV2) -> bytes:
    """Serialize a V2 decision audit payload into deterministic UTF-8 JSON."""

    data = {
        "schema_version": 2,
        "decision_id": payload.decision_id,
        "outcome": payload.outcome,
        "explanation": payload.explanation,
        "event_date": payload.event_date.isoformat(),
        "policy_version": payload.policy_version,
        "journal_sha256": payload.journal_sha256,
    }

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    

def sign_audit_payload(
    payload: DecisionAuditPayload,
    private_key: Ed25519PrivateKey,
) -> bytes:
    """Sign the canonical audit payload using Ed25519."""
    serialized = serialize_audit_payload(payload)
    return private_key.sign(serialized)

def sign_audit_payload_v2(
    payload: DecisionAuditPayloadV2,
    private_key: Ed25519PrivateKey,
) -> bytes:
    """Sign the canonical V2 decision audit payload using Ed25519."""
    serialized = serialize_audit_payload_v2(payload)
    return private_key.sign(serialized)


def verify_audit_signature(
    payload: DecisionAuditPayload,
    signature: bytes,
    public_key: Ed25519PublicKey,
) -> bool:
    """Verify an Ed25519 signature against the canonical audit payload."""
    serialized = serialize_audit_payload(payload)

    try:
        public_key.verify(signature, serialized)
    except InvalidSignature:
        return False

    return True

def verify_audit_signature_v2(
    payload: DecisionAuditPayloadV2,
    signature: bytes,
    public_key: Ed25519PublicKey,
) -> bool:
    """Verify an Ed25519 signature against the canonical V2 audit payload."""

    serialized = serialize_audit_payload_v2(payload)

    try:
        public_key.verify(signature, serialized)
    except InvalidSignature:
        return False

    return True

def verify_signed_journal_entry(
    payload: DecisionAuditPayloadV2,
    journal_entry: str,
    signature: bytes,
    public_key: Ed25519PublicKey,
) -> bool:
    """Verify a signed V2 audit payload against its exact journal entry."""

    if not verify_audit_signature_v2(
        payload=payload,
        signature=signature,
        public_key=public_key,
    ):
        return False

    actual_journal_digest = hash_beancount_entry(journal_entry)

    return actual_journal_digest == payload.journal_sha256


def verify_journal_semantics(
    payload: DecisionAuditPayloadV2,
    journal_entry: str,
) -> bool:
    """Verify that a Beancount decision event agrees with its audit payload."""

    entries, errors, _ = load_string(journal_entry)

    if errors or len(entries) != 1:
        return False

    entry = entries[0]

    if not isinstance(entry, Event):
        return False

    if entry.type != "SigmaVaultDecision":
        return False

    return (
        entry.date == payload.event_date
        and entry.description == f"{payload.decision_id}: {payload.outcome}"
        and entry.meta.get("decision_id") == payload.decision_id
        and entry.meta.get("outcome") == payload.outcome
        and entry.meta.get("explanation") == payload.explanation
    )

def hash_beancount_entry(entry: str) -> str:
    """Compute the SHA-256 digest of a Beancount journal entry."""
    return hashlib.sha256(entry.encode("utf-8")).hexdigest()


def verify_complete_decision_audit(
    payload: DecisionAuditPayloadV2,
    journal_entry: str,
    signature: bytes,
    public_key: Ed25519PublicKey,
) -> bool:
    """Verify signature, journal integrity, and decision semantics."""
    return (
        verify_signed_journal_entry(
            payload=payload,
            journal_entry=journal_entry,
            signature=signature,
            public_key=public_key,
        )
        and verify_journal_semantics(
            payload=payload,
            journal_entry=journal_entry,
        )
    )