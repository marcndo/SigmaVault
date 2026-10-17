import io
import base64
import json
import sqlite3
from datetime import date
from zipfile import ZipFile

import pytest

from decimal import Decimal

from beancount.loader import load_string
from beancount.core.data import Transaction, Event

from sigmavault.pipeline.models import SourceRecordIdentity
from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.signed_financial_repository import (
    SQLiteSignedFinancialRepository,
)
from sigmavault.treasury.signed_financial_transaction import (
    create_signed_financial_record,
    verify_signed_financial_record,
)

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.audit_export import create_audit_export
from sigmavault.treasury.signed_decision_record import (
    create_signed_decision_record,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def make_record(private_key, decision_id):
    return create_signed_decision_record(
        decision=AgentDecision(
            decision_id=decision_id,
            outcome="deferred",
            explanation="Unverified evidence; human review required.",
        ),
        event_date=date(2026, 10, 17),
        policy_version="pilot-v1",
        private_key=private_key,
    )


def test_export_contains_verified_audit_artifacts(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    connection = sqlite3.connect(":memory:")
    repository = SQLiteSignedDecisionRepository(connection)

    repository.save(make_record(private_key, "DECISION-001"))
    repository.save(make_record(private_key, "DECISION-002"))
    connection.commit()

    exported = create_audit_export(
        connection=connection,
        journal_path=tmp_path / "treasury_decisions.beancount",
        public_key=public_key,
    )

    with ZipFile(io.BytesIO(exported)) as archive:
        assert set(archive.namelist()) == {
            "treasury_decisions.beancount",
            "sigmavault_ledger.beancount",
            "signed_decisions.json",
            "public_key.pem",
            "manifest.json",
            "signed_financial_transactions.json",
        }

        decisions = json.loads(
            archive.read("signed_decisions.json")
        )

        manifest = json.loads(
            archive.read("manifest.json")
        )

        assert len(decisions["decisions"]) == 2
        assert manifest["decision_count"] == 2
        assert manifest["includes_executed_transactions"] is False

        journal = archive.read(
            "treasury_decisions.beancount"
        ).decode("utf-8")

        assert "DECISION-001" in journal
        assert "DECISION-002" in journal


def test_export_rejects_tampered_signed_record(tmp_path):
    private_key = Ed25519PrivateKey.generate()

    connection = sqlite3.connect(":memory:")
    repository = SQLiteSignedDecisionRepository(connection)

    repository.save(make_record(private_key, "DECISION-001"))
    connection.commit()

    connection.execute(
        """
        UPDATE signed_decision_records
        SET explanation = ?
        WHERE decision_id = ?
        """,
        ("Tampered explanation", "DECISION-001"),
    )
    connection.commit()

    with pytest.raises(ValueError, match="Invalid signed record"):
        create_audit_export(
            connection=connection,
            journal_path=tmp_path / "treasury_decisions.beancount",
            public_key=private_key.public_key(),
        )


def test_export_rejects_empty_repository(tmp_path):
    private_key = Ed25519PrivateKey.generate()

    connection = sqlite3.connect(":memory:")
    SQLiteSignedDecisionRepository(connection)

    with pytest.raises(
        ValueError,
        match="No signed decisions",
    ):
        create_audit_export(
            connection=connection,
            journal_path=tmp_path / "treasury_decisions.beancount",
            public_key=private_key.public_key(),
        )
        
        
def test_export_contains_combined_ledger(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    connection = sqlite3.connect(":memory:")
    repository = SQLiteSignedDecisionRepository(connection)

    repository.save(make_record(private_key, "DECISION-001"))
    connection.commit()

    exported = create_audit_export(
        connection=connection,
        journal_path=tmp_path / "treasury_decisions.beancount",
        public_key=public_key,
    )

    with ZipFile(io.BytesIO(exported)) as archive:
        assert "sigmavault_ledger.beancount" in archive.namelist()

        ledger = archive.read(
            "sigmavault_ledger.beancount"
        ).decode("utf-8")

        assert 'option "title" "SigmaVault Treasury Ledger"' in ledger
        assert 'option "operating_currency" "XAF"' in ledger
        assert "DECISION-001" in ledger
        assert "SigmaVaultDecision" in ledger

    connection.close()
    
def test_export_contains_signed_financial_transaction_and_ai_decision(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    connection = sqlite3.connect(":memory:")

    decision_repository = SQLiteSignedDecisionRepository(connection)

    explanation = (
        "Agent recommended action: preserve_liquidity. "
        "Agent explanation: Execution is not eligible because "
        "financial evidence is unverified or liquidity is insufficient. "
        "Human review is required. "
        "Human review required; execution not authorized."
    )
    
    decision_id = "AGENT-282bc921ae074c0983db3a3b9f585bdf"
    
    decision = AgentDecision(
        decision_id=decision_id,
        outcome="deferred",
        explanation=explanation,
    )
    
    signed_decision = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 15),
        policy_version="pilot-v1",
        private_key=private_key,
    )
    
    decision_repository.save(signed_decision)
    
    financial_repository = SQLiteSignedFinancialRepository(connection)

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

    signed_transaction = create_signed_financial_record(
        transaction=transaction,
        provenance=provenance,
        transaction_date=date(2026, 10, 16),
        payee="Internet Provider",
        narration="Synthetic monthly internet payment",
        asset_account="Assets:Bank:Operating",
        counterparty_account="Expenses:Internet",
        evidence=b"synthetic-test-evidence",
        private_key=private_key,
    )

    identity = SourceRecordIdentity(
        provider="synthetic_test",
        namespace="obsec_demo",
        record_id="BANK-001",
    )

    financial_repository.save(
        identity=identity,
        record=signed_transaction,
        evidence_reference="synthetic-evidence-001",
    )

    connection.commit()

    exported = create_audit_export(
        connection=connection,
        journal_path=tmp_path / "treasury_decisions.beancount",
        public_key=public_key,
    )

    with ZipFile(io.BytesIO(exported)) as archive:
        assert "sigmavault_ledger.beancount" in archive.namelist()
        financial_data = json.loads(
            archive.read("signed_financial_transactions.json")
        )

        assert (
            financial_data["format"]
            == "sigmavault-signed-financial-transactions-v1"
        )

        assert len(financial_data["transactions"]) == 1

        exported_transaction = financial_data["transactions"][0]

        assert exported_transaction["source_identity"] == {
            "provider": "synthetic_test",
            "namespace": "obsec_demo",
            "record_id": "BANK-001",
        }

        assert exported_transaction["payload"]["transaction_id"] == "BANK-001"
        assert exported_transaction["payload"]["amount"] == "25000"
        assert exported_transaction["payload"]["currency"] == "XAF"

        assert (
            exported_transaction["journal_entry"]
            == signed_transaction.journal_entry
        )

        assert (
        exported_transaction["signature_base64"]
            == base64.b64encode(signed_transaction.signature).decode("ascii")
        )

        assert (
            exported_transaction["evidence_reference"]
            == "synthetic-evidence-001"
        )
        ledger = archive.read(
            "sigmavault_ledger.beancount"
        ).decode("utf-8")

        print("\n========== COMBINED BEANCOUNT LEDGER ==========")
        print(ledger)
        print("==============================================\n")

        # The financial transaction must be present.
        assert "BANK-001" in ledger
        assert "Internet Provider" in ledger
        assert "25000 XAF" in ledger
        assert "Assets:Bank:Operating" in ledger
        assert "Expenses:Internet" in ledger

        # The AI decision must also be present.
        assert decision_id in ledger
        assert "SigmaVaultDecision" in ledger
        assert explanation in ledger
        assert 'outcome: "deferred"' in ledger

        # Validate the complete ledger with Beancount.
        entries, errors, _ = load_string(ledger)

        assert not errors

        transactions = [
            entry for entry in entries
            if isinstance(entry, Transaction)
        ]

        decisions = [
            entry for entry in entries
            if isinstance(entry, Event)
            and entry.type == "SigmaVaultDecision"
        ]

        assert len(transactions) == 1
        assert len(decisions) == 1

        posting_by_account = {
            posting.account: posting.units.number
            for posting in transactions[0].postings
        }

        assert posting_by_account["Assets:Bank:Operating"] == Decimal("-25000")
        assert posting_by_account["Expenses:Internet"] == Decimal("25000")

        # The manifest must cover the combined ledger.
        manifest = json.loads(archive.read("manifest.json"))

        assert "sigmavault_ledger.beancount" in manifest["files"]

    restored = financial_repository.get(identity)

    assert restored is not None

    assert verify_signed_financial_record(
        restored,
        public_key,
        evidence=b"synthetic-test-evidence",
    )

    connection.close()
    
    
def test_export_preserves_full_ai_explanation(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    connection = sqlite3.connect(":memory:")

    repository = SQLiteSignedDecisionRepository(connection)

    explanation = (
        "Agent recommended action: preserve_liquidity. "
        "Agent explanation: Execution is not eligible because "
        "financial evidence is unverified or liquidity is insufficient. "
        "Human review is required. "
        "Human review required; execution not authorized."
    )

    decision_id = "AGENT-282bc921ae074c0983db3a3b9f585bdf"

    decision = AgentDecision(
        decision_id=decision_id,
        outcome="deferred",
        explanation=explanation,
    )

    signed_record = create_signed_decision_record(
        decision=decision,
        event_date=date(2026, 10, 15),
        policy_version="pilot-v1",
        private_key=private_key,
    )

    repository.save(signed_record)
    connection.commit()

    exported = create_audit_export(
        connection=connection,
        journal_path=tmp_path / "treasury_decisions.beancount",
        public_key=private_key.public_key(),
    )

    with ZipFile(io.BytesIO(exported)) as archive:
        ledger = archive.read(
            "sigmavault_ledger.beancount"
        ).decode("utf-8")

        assert decision_id in ledger
        assert explanation in ledger
        assert 'outcome: "deferred"' in ledger
        assert 'event "SigmaVaultDecision"' in ledger

        entries, errors, _ = load_string(ledger)

        assert not errors

        decision_events = [
            entry
            for entry in entries
            if isinstance(entry, Event)
            and entry.type == "SigmaVaultDecision"
        ]

        assert len(decision_events) == 1
        assert decision_events[0].meta["explanation"] == explanation
        assert decision_events[0].meta["decision_id"] == decision_id

    connection.close()