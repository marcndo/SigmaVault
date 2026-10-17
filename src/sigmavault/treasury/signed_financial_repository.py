"""SQLite persistence for signed financial transactions."""

import json
import sqlite3
from datetime import date

from sigmavault.pipeline.models import SourceRecordIdentity
from sigmavault.treasury.signed_financial_transaction import (
    FinancialTransactionAuditPayloadV1,
    SignedFinancialTransactionRecord,
    serialize_financial_payload,
)


class SQLiteSignedFinancialRepository:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS signed_financial_records (
                provider TEXT NOT NULL,
                namespace TEXT NOT NULL,
                record_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                journal_entry TEXT NOT NULL,
                signature BLOB NOT NULL,
                evidence_reference TEXT NOT NULL,
                PRIMARY KEY (provider, namespace, record_id)
            )
            """
        )

    def save(
        self,
        *,
        identity: SourceRecordIdentity,
        record: SignedFinancialTransactionRecord,
        evidence_reference: str,
    ) -> bool:
        """Insert a record; return False for an identical retry.

        The caller owns the database transaction and must commit.
        """

        if not isinstance(evidence_reference, str) or not evidence_reference.strip():
            raise ValueError("Evidence reference must not be blank")

        if identity.record_id != record.payload.transaction_id:
            raise ValueError("Source identity and signed transaction ID differ")

        payload_json = serialize_financial_payload(record.payload).decode("utf-8")

        values = (
            identity.provider,
            identity.namespace,
            identity.record_id,
            payload_json,
            record.journal_entry,
            record.signature,
            evidence_reference,
        )

        existing = self.connection.execute(
            """
            SELECT payload_json, journal_entry, signature, evidence_reference
            FROM signed_financial_records
            WHERE provider = ? AND namespace = ? AND record_id = ?
            """,
            (
                identity.provider,
                identity.namespace,
                identity.record_id,
            ),
        ).fetchone()

        if existing is not None:
            if tuple(existing) == values[3:]:
                return False
            raise ValueError("Conflicting financial transaction identity")

        try:
            self.connection.execute(
                """
                INSERT INTO signed_financial_records (
                    provider, namespace, record_id,
                    payload_json, journal_entry, signature,
                    evidence_reference
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError(
                "Conflicting financial transaction identity"
            ) from exc

        return True

    def get(
        self,
        identity: SourceRecordIdentity,
    ) -> SignedFinancialTransactionRecord | None:
        row = self.connection.execute(
            """
            SELECT payload_json, journal_entry, signature
            FROM signed_financial_records
            WHERE provider = ? AND namespace = ? AND record_id = ?
            """,
            (
                identity.provider,
                identity.namespace,
                identity.record_id,
            ),
        ).fetchone()

        if row is None:
            return None

        data = json.loads(row[0])

        payload = FinancialTransactionAuditPayloadV1(
            transaction_id=data["transaction_id"],
            source=data["source"],
            amount=data["amount"],
            currency=data["currency"],
            direction=data["direction"],
            transaction_date=date.fromisoformat(data["transaction_date"]),
            asset_account=data["asset_account"],
            counterparty_account=data["counterparty_account"],
            journal_sha256=data["journal_sha256"],
            evidence_sha256=data["evidence_sha256"],
        )

        return SignedFinancialTransactionRecord(
            payload=payload,
            journal_entry=row[1],
            signature=bytes(row[2]),
        )