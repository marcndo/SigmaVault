import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.pipeline.models import SourceRecordIdentity
from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.signed_financial_transaction import (
    create_signed_financial_record,
    verify_signed_financial_record,
)
from sigmavault.treasury.signed_financial_repository import (
    SQLiteSignedFinancialRepository,
)


@pytest.fixture
def setup():
    connection = sqlite3.connect(":memory:")
    repository = SQLiteSignedFinancialRepository(connection)
    private_key = Ed25519PrivateKey.generate()

    identity = SourceRecordIdentity(
        provider="bank",
        namespace="obsec-operating",
        record_id="BANK-001",
    )

    transaction = FinancialTransaction(
        transaction_id="BANK-001",
        amount=Decimal("25000"),
        currency="XAF",
        status="actual",
        direction="expense",
    )

    provenance = TransactionProvenance(
        transaction_id="BANK-001",
        source="verified_bank_statement",
        verified=True,
    )

    record = create_signed_financial_record(
        transaction=transaction,
        provenance=provenance,
        transaction_date=date(2026, 10, 17),
        payee="Internet Provider",
        narration="Synthetic internet payment",
        asset_account="Assets:Bank:Operating",
        counterparty_account="Expenses:Internet",
        evidence=b"synthetic-bank-evidence",
        private_key=private_key,
    )

    yield connection, repository, private_key, identity, record

    connection.close()


def test_save_and_retrieve(setup):
    connection, repository, key, identity, record = setup

    with connection:
        assert repository.save(
            identity=identity,
            record=record,
            evidence_reference="synthetic-evidence-001",
        )

    restored = repository.get(identity)

    assert restored == record
    assert verify_signed_financial_record(
        restored,
        key.public_key(),
        evidence=b"synthetic-bank-evidence",
    )


def test_identical_retry_does_not_duplicate(setup):
    connection, repository, _, identity, record = setup

    with connection:
        assert repository.save(
            identity=identity,
            record=record,
            evidence_reference="synthetic-evidence-001",
        )

        assert not repository.save(
            identity=identity,
            record=record,
            evidence_reference="synthetic-evidence-001",
        )

    count = connection.execute(
        "SELECT COUNT(*) FROM signed_financial_records"
    ).fetchone()[0]

    assert count == 1


def test_conflicting_retry_is_rejected(setup):
    connection, repository, _, identity, record = setup

    with connection:
        repository.save(
            identity=identity,
            record=record,
            evidence_reference="synthetic-evidence-001",
        )

    with pytest.raises(ValueError, match="Conflicting"):
        repository.save(
            identity=identity,
            record=record,
            evidence_reference="different-evidence-reference",
        )


def test_rollback_removes_uncommitted_record(setup):
    connection, repository, _, identity, record = setup

    with pytest.raises(RuntimeError):
        with connection:
            repository.save(
                identity=identity,
                record=record,
                evidence_reference="synthetic-evidence-001",
            )
            raise RuntimeError("Simulated failure")

    assert repository.get(identity) is None


def test_missing_record_returns_none(setup):
    _, repository, _, identity, _ = setup

    assert repository.get(identity) is None