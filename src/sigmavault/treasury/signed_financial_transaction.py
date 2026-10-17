"""Cryptographic audit records for verified financial transactions."""

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from beancount.core.data import Transaction
from beancount.parser.parser import parse_string
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.beancount_transaction import (
    render_financial_transaction,
)
from sigmavault.treasury.signed_decision_audit import (
    hash_beancount_entry,
)


@dataclass(frozen=True)
class FinancialTransactionAuditPayloadV1:
    transaction_id: str
    source: str
    amount: str
    currency: str
    direction: str
    transaction_date: date
    asset_account: str
    counterparty_account: str
    journal_sha256: str
    evidence_sha256: str


@dataclass(frozen=True)
class SignedFinancialTransactionRecord:
    payload: FinancialTransactionAuditPayloadV1
    journal_entry: str
    signature: bytes


def serialize_financial_payload(
    payload: FinancialTransactionAuditPayloadV1,
) -> bytes:
    data = {
        "schema_version": 1,
        "record_type": "financial_transaction",
        "transaction_id": payload.transaction_id,
        "source": payload.source,
        "amount": payload.amount,
        "currency": payload.currency,
        "direction": payload.direction,
        "transaction_date": payload.transaction_date.isoformat(),
        "asset_account": payload.asset_account,
        "counterparty_account": payload.counterparty_account,
        "journal_sha256": payload.journal_sha256,
        "evidence_sha256": payload.evidence_sha256,
    }

    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def create_signed_financial_record(
    *,
    transaction: FinancialTransaction,
    provenance: TransactionProvenance,
    transaction_date: date,
    payee: str,
    narration: str,
    asset_account: str,
    counterparty_account: str,
    evidence: bytes,
    private_key: Ed25519PrivateKey,
) -> SignedFinancialTransactionRecord:
    if not isinstance(evidence, bytes) or not evidence:
        raise ValueError("Nonempty evidence bytes are required")

    journal_entry = render_financial_transaction(
        transaction=transaction,
        provenance=provenance,
        transaction_date=transaction_date,
        payee=payee,
        narration=narration,
        asset_account=asset_account,
        counterparty_account=counterparty_account,
    )

    payload = FinancialTransactionAuditPayloadV1(
        transaction_id=transaction.transaction_id,
        source=provenance.source,
        amount=format(transaction.amount, "f"),
        currency=transaction.currency,
        direction=transaction.direction,
        transaction_date=transaction_date,
        asset_account=asset_account,
        counterparty_account=counterparty_account,
        journal_sha256=hash_beancount_entry(journal_entry),
        evidence_sha256=hashlib.sha256(evidence).hexdigest(),
    )

    return SignedFinancialTransactionRecord(
        payload=payload,
        journal_entry=journal_entry,
        signature=private_key.sign(
            serialize_financial_payload(payload)
        ),
    )


def verify_signed_financial_record(
    record: SignedFinancialTransactionRecord,
    public_key: Ed25519PublicKey,
    evidence: bytes | None = None,
) -> bool:
    payload = record.payload

    try:
        public_key.verify(
            record.signature,
            serialize_financial_payload(payload),
        )
    except (InvalidSignature, ValueError, TypeError):
        return False

    if hash_beancount_entry(record.journal_entry) != payload.journal_sha256:
        return False

    if evidence is not None:
        if hashlib.sha256(evidence).hexdigest() != payload.evidence_sha256:
            return False

    entries, errors, _ = parse_string(record.journal_entry)

    if errors or len(entries) != 1:
        return False

    entry = entries[0]

    if not isinstance(entry, Transaction):
        return False

    if entry.date != payload.transaction_date:
        return False

    if entry.meta.get("source_id") != payload.transaction_id:
        return False

    if entry.meta.get("source_provider") != payload.source:
        return False

    if len(entry.postings) != 2:
        return False

    asset_posting, counterparty_posting = entry.postings

    if asset_posting.account != payload.asset_account:
        return False

    if counterparty_posting.account != payload.counterparty_account:
        return False

    if any(
        posting.units.currency != payload.currency
        for posting in entry.postings
    ):
        return False

    try:
        amount = Decimal(payload.amount)
    except (ValueError, ArithmeticError):
        return False

    if not amount.is_finite() or amount <= 0:
        return False

    if payload.direction == "expense":
        expected_asset = -amount
        expected_counterparty = amount
    elif payload.direction == "income":
        expected_asset = amount
        expected_counterparty = -amount
    else:
        return False

    return (
        asset_posting.units.number == expected_asset
        and counterparty_posting.units.number == expected_counterparty
    )