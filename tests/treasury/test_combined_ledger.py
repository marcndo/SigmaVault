import sqlite3
from datetime import date
from decimal import Decimal

from beancount.loader import load_string
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.pipeline.models import SourceRecordIdentity
from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.signed_financial_repository import (
    SQLiteSignedFinancialRepository,
)
from sigmavault.treasury.signed_financial_transaction import (
    create_signed_financial_record,
)
from sigmavault.treasury.combined_ledger import (
    build_combined_ledger,
)


def test_combined_ledger_contains_verified_financial_transaction():
    connection = sqlite3.connect(":memory:")
    private_key = Ed25519PrivateKey.generate()

    repository = SQLiteSignedFinancialRepository(connection)

    transaction = FinancialTransaction(
        transaction_id="BANK-001",
        amount=Decimal("25000"),
        currency="XAF",
        status="actual",
        direction="expense",
    )

    provenance = TransactionProvenance(
        transaction_id="BANK-001",
        source="synthetic_verified_fixture",
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
        evidence=b"synthetic-evidence",
        private_key=private_key,
    )

    with connection:
        repository.save(
            identity=SourceRecordIdentity(
                provider="bank",
                namespace="test",
                record_id="BANK-001",
            ),
            record=record,
            evidence_reference="synthetic-test-evidence",
        )

    ledger = build_combined_ledger(
        connection=connection,
        public_key=private_key.public_key(),
    )

    assert 'option "title" "SigmaVault Treasury Ledger"' in ledger
    assert "Assets:Bank:Operating" in ledger
    assert "Expenses:Internet" in ledger
    assert "25000 XAF" in ledger
    assert "BANK-001" in ledger

    entries, errors, _ = load_string(ledger)

    assert not errors
    assert entries

    connection.close()