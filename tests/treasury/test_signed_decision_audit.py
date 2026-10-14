from datetime import date
import json
import pytest
from dataclasses import replace
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.signed_decision_audit import (
    DecisionAuditPayload,
    serialize_audit_payload,
    sign_audit_payload,
    verify_audit_signature,
    hash_beancount_entry,
    DecisionAuditPayloadV2,
    serialize_audit_payload_v2,
    sign_audit_payload_v2,
    verify_audit_signature_v2,
    verify_signed_journal_entry,
)


def test_decision_audit_payload_preserves_required_fields():
    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    assert payload.decision_id == "DEC-001"
    assert payload.outcome == "approved"
    assert payload.explanation == (
        "The required liquidity reserve is preserved."
    )
    assert payload.event_date == date(2026, 10, 14)
    assert payload.policy_version == "1.0.0"
    
@pytest.mark.parametrize(
    "decision_id",
    ["", " ", "   ", "\t", "\n"],
)
def test_decision_audit_payload_rejects_blank_decision_id(
    decision_id: str,
):
    with pytest.raises(
        ValueError,
        match="Decision audit ID must not be blank",
    ):
        DecisionAuditPayload(
            decision_id=decision_id,
            outcome="approved",
            explanation="The liquidity reserve is preserved.",
            event_date=date(2026, 10, 14),
            policy_version="1.0.0",
        )
        
        
@pytest.mark.parametrize(
    "outcome",
    [
        "",
        "pending",
        "executed",
        "APPROVED",
        "approved ",
        None,
        123,
        [],
        {},
    ],
)
def test_decision_audit_payload_rejects_invalid_outcome(
    outcome,
):
    with pytest.raises(
        ValueError,
        match="Invalid decision audit outcome",
    ):
        DecisionAuditPayload(
            decision_id="DEC-001",
            outcome=outcome,
            explanation="The required liquidity reserve is preserved.",
            event_date=date(2026, 10, 14),
            policy_version="1.0.0",
        )
        
        
@pytest.mark.parametrize(
    "explanation",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        None,
        123,
        [],
        {},
    ],
)
def test_decision_audit_payload_rejects_invalid_explanation(
    explanation,
):
    with pytest.raises(
        ValueError,
        match="Decision audit explanation must not be blank",
    ):
        DecisionAuditPayload(
            decision_id="DEC-001",
            outcome="approved",
            explanation=explanation,
            event_date=date(2026, 10, 14),
            policy_version="1.0.0",
        )
        
from datetime import datetime


@pytest.mark.parametrize(
    "event_date",
    [
        None,
        "",
        "2026-10-14",
        123,
        3.14,
        [],
        {},
        datetime(2026, 10, 14, 12, 30),
    ],
)
def test_decision_audit_payload_rejects_invalid_event_date(
    event_date,
):
    with pytest.raises(
        ValueError,
        match="Decision audit event date must be a date",
    ):
        DecisionAuditPayload(
            decision_id="DEC-001",
            outcome="approved",
            explanation="The required liquidity reserve is preserved.",
            event_date=event_date,
            policy_version="1.0.0",
        )
        
@pytest.mark.parametrize(
    "policy_version",
    [
        "",
        " ",
        "   ",
        "\t",
        "\n",
        None,
        123,
        [],
        {},
    ],
)
def test_decision_audit_payload_rejects_invalid_policy_version(
    policy_version,
):
    with pytest.raises(
        ValueError,
        match="Decision audit policy version must not be blank",
    ):
        DecisionAuditPayload(
            decision_id="DEC-001",
            outcome="approved",
            explanation="The required liquidity reserve is preserved.",
            event_date=date(2026, 10, 14),
            policy_version=policy_version,
        )
        
        
def test_serialize_audit_payload_produces_canonical_utf8_bytes():
    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    result = serialize_audit_payload(payload)

    expected = {
        "schema_version": 1,
        "decision_id": "DEC-001",
        "outcome": "approved",
        "explanation": "The required liquidity reserve is preserved.",
        "event_date": "2026-10-14",
        "policy_version": "1.0.0",
    }

    assert isinstance(result, bytes)

    assert result == json.dumps(
        expected,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    
    
def test_equivalent_audit_payloads_produce_identical_bytes():
    first = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    second = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    assert first is not second
    assert first == second

    first_bytes = serialize_audit_payload(first)
    second_bytes = serialize_audit_payload(second)

    assert first_bytes == second_bytes
    
    
def test_serialize_audit_payload_preserves_unicode_and_special_characters():
    explanation = (
        'Réserve de trésorerie: €1,500.\n'
        'The agent said: "Allocation deferred".\n'
        r"Evidence location: C:\reports\trésorerie.txt"
    )

    payload = DecisionAuditPayload(
        decision_id="DEC-É-001",
        outcome="deferred",
        explanation=explanation,
        event_date=date(2026, 10, 14),
        policy_version="policy-v1",
    )

    serialized = serialize_audit_payload(payload)

    assert isinstance(serialized, bytes)

    decoded = json.loads(serialized.decode("utf-8"))

    assert decoded["decision_id"] == payload.decision_id
    assert decoded["outcome"] == payload.outcome
    assert decoded["explanation"] == explanation
    assert decoded["event_date"] == "2026-10-14"
    assert decoded["policy_version"] == payload.policy_version

    assert "Réserve".encode("utf-8") in serialized
    assert "€".encode("utf-8") in serialized
    
    
def test_serialized_audit_payload_includes_schema_version():
    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    serialized = serialize_audit_payload(payload)

    decoded = json.loads(serialized.decode("utf-8"))

    assert decoded["schema_version"] == 1
    
    
def test_sign_audit_payload_produces_verifiable_ed25519_signature():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    signature = sign_audit_payload(
        payload=payload,
        private_key=private_key,
    )

    assert isinstance(signature, bytes)
    assert len(signature) == 64

    public_key.verify(
        signature,
        serialize_audit_payload(payload),
    )
    
def test_verify_audit_signature_accepts_valid_signature():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    signature = sign_audit_payload(
        payload=payload,
        private_key=private_key,
    )

    result = verify_audit_signature(
        payload=payload,
        signature=signature,
        public_key=public_key,
    )

    assert result is True
    
def test_verify_audit_signature_rejects_tampered_explanation():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    original_payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    signature = sign_audit_payload(
        payload=original_payload,
        private_key=private_key,
    )

    tampered_payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="All financial obligations have been settled.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    assert verify_audit_signature(
        payload=original_payload,
        signature=signature,
        public_key=public_key,
    ) is True

    assert verify_audit_signature(
        payload=tampered_payload,
        signature=signature,
        public_key=public_key,
    ) is False
    
    
@pytest.mark.parametrize(
    ("field_name", "tampered_value"),
    [
        ("decision_id", "DEC-999"),
        ("outcome", "rejected"),
        ("event_date", date(2026, 10, 15)),
        ("policy_version", "2.0.0"),
    ],
)
def test_verify_audit_signature_rejects_tampered_fields(
    field_name,
    tampered_value,
):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    original_payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    signature = sign_audit_payload(
        payload=original_payload,
        private_key=private_key,
    )

    tampered_payload = replace(
        original_payload,
        **{field_name: tampered_value},
    )

    assert verify_audit_signature(
        payload=original_payload,
        signature=signature,
        public_key=public_key,
    ) is True

    assert verify_audit_signature(
        payload=tampered_payload,
        signature=signature,
        public_key=public_key,
    ) is False
    
    
def test_verify_audit_signature_rejects_wrong_public_key():
    signing_private_key = Ed25519PrivateKey.generate()
    signing_public_key = signing_private_key.public_key()

    unrelated_private_key = Ed25519PrivateKey.generate()
    unrelated_public_key = unrelated_private_key.public_key()

    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    signature = sign_audit_payload(
        payload=payload,
        private_key=signing_private_key,
    )

    assert verify_audit_signature(
        payload=payload,
        signature=signature,
        public_key=signing_public_key,
    ) is True

    assert verify_audit_signature(
        payload=payload,
        signature=signature,
        public_key=unrelated_public_key,
    ) is False
    
    
def test_verify_audit_signature_rejects_corrupted_signature():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    signature = sign_audit_payload(
        payload=payload,
        private_key=private_key,
    )

    assert verify_audit_signature(
        payload=payload,
        signature=signature,
        public_key=public_key,
    ) is True

    corrupted_signature = bytearray(signature)
    corrupted_signature[0] ^= 0x01

    assert verify_audit_signature(
        payload=payload,
        signature=bytes(corrupted_signature),
        public_key=public_key,
    ) is False
    
@pytest.mark.parametrize(
    "malformed_signature",
    [
        b"",
        b"\x00",
        b"\x00" * 32,
        b"\x00" * 63,
        b"\x00" * 65,
        b"\x00" * 128,
    ],
)
def test_verify_audit_signature_rejects_malformed_signature(
    malformed_signature: bytes,
):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    payload = DecisionAuditPayload(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The required liquidity reserve is preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
    )

    assert verify_audit_signature(
        payload=payload,
        signature=malformed_signature,
        public_key=public_key,
    ) is False
    
def test_hash_beancount_entry_is_deterministic_and_content_sensitive():
    original_entry = (
        '2026-10-14 event "SigmaVault Decision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    modified_entry = (
        '2026-10-14 event "SigmaVault Decision" '
        '"DEC-001: approved - Reserve depleted."\n'
    )

    original_digest = hash_beancount_entry(original_entry)

    assert isinstance(original_digest, str)
    assert len(original_digest) == 64
    assert original_digest == hash_beancount_entry(original_entry)
    assert original_digest != hash_beancount_entry(modified_entry)
    
def test_decision_audit_payload_v2_contains_journal_digest():
    journal_entry = (
        '2026-10-14 event "SigmaVault Decision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    journal_digest = hash_beancount_entry(journal_entry)

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=journal_digest,
    )

    assert payload.decision_id == "DEC-001"
    assert payload.outcome == "approved"
    assert payload.journal_sha256 == journal_digest
    assert len(payload.journal_sha256) == 64
    
    
def test_serialize_audit_payload_v2_produces_canonical_json():
    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    journal_digest = hash_beancount_entry(journal_entry)

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=journal_digest,
    )

    serialized = serialize_audit_payload_v2(payload)

    expected = json.dumps(
        {
            "schema_version": 2,
            "decision_id": "DEC-001",
            "outcome": "approved",
            "explanation": "Reserve preserved.",
            "event_date": "2026-10-14",
            "policy_version": "1.0.0",
            "journal_sha256": journal_digest,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")

    assert isinstance(serialized, bytes)
    assert serialized == expected
    assert serialize_audit_payload_v2(payload) == serialized
    

def test_sign_audit_payload_v2_produces_valid_ed25519_signature():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(journal_entry),
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=private_key,
    )

    assert isinstance(signature, bytes)
    assert len(signature) == 64

    public_key.verify(
        signature,
        serialize_audit_payload_v2(payload),
    )
    
    
def test_verify_audit_signature_v2_accepts_valid_signature():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(journal_entry),
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=private_key,
    )

    assert verify_audit_signature_v2(
        payload=payload,
        signature=signature,
        public_key=public_key,
    ) is True
    

def test_verify_signed_journal_entry_accepts_matching_journal():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(journal_entry),
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=private_key,
    )

    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=journal_entry,
        signature=signature,
        public_key=public_key,
    ) is True
    
    
def test_verify_signed_journal_entry_rejects_tampered_journal():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    original_journal = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    tampered_journal = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve depleted."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(original_journal),
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=private_key,
    )

    # The original signature remains cryptographically valid.
    assert verify_audit_signature_v2(
        payload=payload,
        signature=signature,
        public_key=public_key,
    ) is True

    # The original journal matches the signed digest.
    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=original_journal,
        signature=signature,
        public_key=public_key,
    ) is True

    # The modified journal must fail verification.
    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=tampered_journal,
        signature=signature,
        public_key=public_key,
    ) is False
    
    
    
def test_verify_signed_journal_entry_rejects_corrupted_signature():
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(journal_entry),
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=private_key,
    )

    corrupted_signature = bytearray(signature)
    corrupted_signature[0] ^= 0x01

    assert hash_beancount_entry(journal_entry) == payload.journal_sha256

    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=journal_entry,
        signature=signature,
        public_key=public_key,
    ) is True

    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=journal_entry,
        signature=bytes(corrupted_signature),
        public_key=public_key,
    ) is False
    
def test_verify_signed_journal_entry_rejects_wrong_public_key():
    signing_private_key = Ed25519PrivateKey.generate()
    signing_public_key = signing_private_key.public_key()

    unrelated_private_key = Ed25519PrivateKey.generate()
    unrelated_public_key = unrelated_private_key.public_key()

    journal_entry = (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-001: approved - Reserve preserved."\n'
    )

    payload = DecisionAuditPayloadV2(
        decision_id="DEC-001",
        outcome="approved",
        explanation="Reserve preserved.",
        event_date=date(2026, 10, 14),
        policy_version="1.0.0",
        journal_sha256=hash_beancount_entry(journal_entry),
    )

    signature = sign_audit_payload_v2(
        payload=payload,
        private_key=signing_private_key,
    )

    # Verification succeeds with the corresponding public key.
    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=journal_entry,
        signature=signature,
        public_key=signing_public_key,
    ) is True

    # Verification fails with an unrelated public key.
    assert verify_signed_journal_entry(
        payload=payload,
        journal_entry=journal_entry,
        signature=signature,
        public_key=unrelated_public_key,
    ) is False