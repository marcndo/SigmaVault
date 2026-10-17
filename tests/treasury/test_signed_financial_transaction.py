from dataclasses import replace
from datetime import date
from decimal import Decimal

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.signed_financial_transaction import (
    create_signed_financial_record,
    verify_signed_financial_record,
)


@pytest.fixture
def private_key():
    return Ed25519PrivateKey.generate()


@pytest.fixture
def transaction():
    return FinancialTransaction(
        transaction_id="BANK-001",
        amount=Decimal("25000"),
        currency="XAF",
        status="actual",
        direction="expense",
    )


@pytest.fixture
def provenance():
    return TransactionProvenance(
        transaction_id="BANK-001",
        source="verified_bank_statement",
        verified=True,
    )


def make_record(private_key, transaction, provenance):
    return create_signed_financial_record(
        transaction=transaction,
        provenance=provenance,
        transaction_date=date(2026, 10, 17),
        payee="Internet Provider",
        narration="Monthly internet payment",
        asset_account="Assets:Bank:Operating",
        counterparty_account="Expenses:Internet",
        evidence=b"synthetic-bank-evidence",
        private_key=private_key,
    )


def test_valid_signed_record(private_key, transaction, provenance):
    record = make_record(private_key, transaction, provenance)

    assert verify_signed_financial_record(
        record,
        private_key.public_key(),
        evidence=b"synthetic-bank-evidence",
    )


def test_modified_journal_is_rejected(private_key, transaction, provenance):
    record = make_record(private_key, transaction, provenance)

    modified = replace(
        record,
        journal_entry=record.journal_entry.replace(
            "25000", "35000"
        ),
    )

    assert not verify_signed_financial_record(
        modified,
        private_key.public_key(),
    )


def test_modified_payload_is_rejected(private_key, transaction, provenance):
    record = make_record(private_key, transaction, provenance)

    modified = replace(
        record,
        payload=replace(record.payload, amount="35000"),
    )

    assert not verify_signed_financial_record(
        modified,
        private_key.public_key(),
    )


def test_modified_evidence_is_rejected(private_key, transaction, provenance):
    record = make_record(private_key, transaction, provenance)

    assert not verify_signed_financial_record(
        record,
        private_key.public_key(),
        evidence=b"different-evidence",
    )


def test_wrong_key_is_rejected(private_key, transaction, provenance):
    record = make_record(private_key, transaction, provenance)

    wrong_key = Ed25519PrivateKey.generate()

    assert not verify_signed_financial_record(
        record,
        wrong_key.public_key(),
    )


def test_forecast_is_rejected(private_key, transaction, provenance):
    forecast = replace(transaction, status="forecast")

    with pytest.raises(ValueError, match="not an actual"):
        make_record(private_key, forecast, provenance)


def test_unverified_transaction_is_rejected(
    private_key, transaction, provenance
):
    unverified = replace(provenance, verified=False)

    with pytest.raises(ValueError, match="not verified"):
        make_record(private_key, transaction, unverified)