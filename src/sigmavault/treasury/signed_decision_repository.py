from typing import Protocol

from sigmavault.treasury.signed_decision_record import (
    SignedDecisionRecord,
)
import sqlite3
from datetime import date

from sigmavault.treasury.signed_decision_audit import (
    DecisionAuditPayloadV2,
)


class SignedDecisionRepository(Protocol):
    """Contract for storing and retrieving signed decision records."""

    def save(self, record: SignedDecisionRecord) -> None:
        """Persist a signed decision record."""
        ...

    def get_by_decision_id(
        self,
        decision_id: str,
    ) -> SignedDecisionRecord | None:
        """Retrieve a signed record by its decision ID, if present."""
        ...
        
class SQLiteSignedDecisionRepository:
    """SQLite storage for signed treasury decision records."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS signed_decision_records (
                decision_id TEXT PRIMARY KEY,
                outcome TEXT NOT NULL,
                explanation TEXT NOT NULL,
                event_date TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                journal_sha256 TEXT NOT NULL,
                journal_entry TEXT NOT NULL,
                signature BLOB NOT NULL
            )
            """
        )

    def save(self, record: SignedDecisionRecord) -> None:
        """Store a signed decision record without committing."""

        payload = record.payload

        self.connection.execute(
            """
            INSERT INTO signed_decision_records (
                decision_id,
                outcome,
                explanation,
                event_date,
                policy_version,
                journal_sha256,
                journal_entry,
                signature
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.decision_id,
                payload.outcome,
                payload.explanation,
                payload.event_date.isoformat(),
                payload.policy_version,
                payload.journal_sha256,
                record.journal_entry,
                record.signature,
            ),
        )

    def get_by_decision_id(
        self,
        decision_id: str,
    ) -> SignedDecisionRecord | None:
        """Retrieve a signed record without modifying its artifacts."""

        cursor = self.connection.execute(
            """
            SELECT
                decision_id,
                outcome,
                explanation,
                event_date,
                policy_version,
                journal_sha256,
                journal_entry,
                signature
            FROM signed_decision_records
            WHERE decision_id = ?
            """,
            (decision_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        (
            stored_decision_id,
            outcome,
            explanation,
            event_date,
            policy_version,
            journal_sha256,
            journal_entry,
            signature,
        ) = row

        payload = DecisionAuditPayloadV2(
            decision_id=stored_decision_id,
            outcome=outcome,
            explanation=explanation,
            event_date=date.fromisoformat(event_date),
            policy_version=policy_version,
            journal_sha256=journal_sha256,
        )

        return SignedDecisionRecord(
            payload=payload,
            journal_entry=journal_entry,
            signature=signature,
        )