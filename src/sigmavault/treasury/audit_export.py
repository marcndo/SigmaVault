"""Portable export of verified SigmaVault treasury decision audits."""

import base64
import hashlib
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
from sigmavault.treasury.combined_ledger import build_combined_ledger
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)
from sigmavault.pipeline.models import SourceRecordIdentity
from sigmavault.treasury.signed_financial_repository import (
    SQLiteSignedFinancialRepository,
)
from sigmavault.treasury.signed_financial_transaction import (
    serialize_financial_payload,
    verify_signed_financial_record,
)
from sigmavault.treasury.journal_synchronizer import synchronize_journal
from sigmavault.treasury.signed_decision_audit import (
    serialize_audit_payload_v2,
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def create_audit_export(
    connection: sqlite3.Connection,
    journal_path: str | Path,
    public_key: Ed25519PublicKey,
) -> bytes:
    """Export verified signed decisions and their Beancount journal."""

    journal_path = Path(journal_path)

    # Verify stored decisions and reconcile the journal.
    record_count = synchronize_journal(
        connection=connection,
        journal_path=journal_path,
        public_key=public_key,
    )

    repository = SQLiteSignedDecisionRepository(connection)

    decision_ids = [
        row[0]
        for row in connection.execute(
            """
            SELECT decision_id
            FROM signed_decision_records
            ORDER BY rowid
            """
        ).fetchall()
    ]

    if not decision_ids:
        raise ValueError("No signed decisions are available for export")

    signed_decisions = []

    for decision_id in decision_ids:
        record = repository.get_by_decision_id(decision_id)

        if record is None:
            raise RuntimeError(
                f"Missing signed decision: {decision_id}"
            )

        if not verify_complete_decision_audit(
            payload=record.payload,
            journal_entry=record.journal_entry,
            signature=record.signature,
            public_key=public_key,
        ):
            raise ValueError(
                f"Invalid signed decision: {decision_id}"
            )

        signed_decisions.append(
            {
                "payload": json.loads(
                    serialize_audit_payload_v2(
                        record.payload
                    ).decode("utf-8")
                ),
                "journal_entry": record.journal_entry,
                "signature_base64": base64.b64encode(
                    record.signature
                ).decode("ascii"),
            }
        )

    journal_bytes = journal_path.read_bytes()

    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    signed_decisions_bytes = json.dumps(
        {
            "format": "sigmavault-signed-decisions-v1",
            "decisions": signed_decisions,
        },
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")
    combined_ledger = build_combined_ledger(
    connection=connection,
    public_key=public_key,
)

    combined_ledger_bytes = combined_ledger.encode("utf-8")
    financial_repository = SQLiteSignedFinancialRepository(connection)

    financial_rows = connection.execute(
        """
        SELECT provider, namespace, record_id, evidence_reference
        FROM signed_financial_records
        ORDER BY rowid
        """
    ).fetchall()

    signed_financial_transactions = []

    for provider, namespace, record_id, evidence_reference in financial_rows:
        identity = SourceRecordIdentity(
            provider=provider,
            namespace=namespace,
            record_id=record_id,
        )

        record = financial_repository.get(identity)

        if record is None or not verify_signed_financial_record(
            record,
            public_key,
        ):
            raise ValueError(
                f"Invalid signed financial record: {identity}"
            )

        signed_financial_transactions.append(
            {
                "source_identity": {
                    "provider": provider,
                    "namespace": namespace,
                    "record_id": record_id,
                },
                "payload": json.loads(
                    serialize_financial_payload(record.payload).decode("utf-8")
                ),
                "journal_entry": record.journal_entry,
                "signature_base64": base64.b64encode(
                    record.signature
                ).decode("ascii"),
                "evidence_reference": evidence_reference,
            }
        )

    signed_financial_bytes = json.dumps(
        {
            "format": "sigmavault-signed-financial-transactions-v1",
            "transactions": signed_financial_transactions,
        },
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")
    files = {
        "treasury_decisions.beancount": journal_bytes,
        "sigmavault_ledger.beancount": combined_ledger_bytes,
        "signed_decisions.json": signed_decisions_bytes,
        "signed_financial_transactions.json": signed_financial_bytes,
        "public_key.pem": public_key_bytes,
    }

    manifest = {
        "format": "sigmavault-audit-export-v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "decision_count": record_count,
        "scope": "signed_treasury_decisions_only",
        "includes_executed_transactions": False,
        "signature_algorithm": "Ed25519",
        "files": {
            filename: {
                "sha256": hashlib.sha256(contents).hexdigest(),
                "size_bytes": len(contents),
            }
            for filename, contents in files.items()
        },
    }

    manifest_bytes = json.dumps(
        manifest,
        indent=2,
        ensure_ascii=False,
    ).encode("utf-8")

    output = io.BytesIO()

    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for filename, contents in files.items():
            archive.writestr(filename, contents)

        archive.writestr("manifest.json", manifest_bytes)

    return output.getvalue()