import io
import json
import sqlite3
from datetime import date
from zipfile import ZipFile

import pytest

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
            "signed_decisions.json",
            "public_key.pem",
            "manifest.json",
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