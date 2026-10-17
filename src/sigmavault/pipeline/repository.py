import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

from sigmavault.pipeline.models import CanonicalFinancialRecord


def serialize_record(record: CanonicalFinancialRecord) -> str:
    """Produce deterministic JSON for record comparison."""

    return json.dumps(
        asdict(record),
        sort_keys=True,
        separators=(",", ":"),
        default=_serialize_value,
    )


def _serialize_value(value):
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, date):
        return value.isoformat()

    raise TypeError(f"Unsupported value: {type(value).__name__}")


class SQLiteIngestionRepository:
    """Persist canonical financial records with source-scoped identities."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ingested_financial_records (
                        provider TEXT NOT NULL,
                        namespace TEXT NOT NULL,
                        record_id TEXT NOT NULL,
                        record_json TEXT NOT NULL,
                        PRIMARY KEY (provider, namespace, record_id)
                    )
                    """
                )

    def record(self, record: CanonicalFinancialRecord) -> str:
        """Return inserted, duplicate, or conflict."""

        identity = record.identity
        payload = serialize_record(record)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO ingested_financial_records (
                        provider, namespace, record_id, record_json
                    )
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (provider, namespace, record_id)
                    DO NOTHING
                    """,
                    (
                        identity.provider,
                        identity.namespace,
                        identity.record_id,
                        payload,
                    ),
                )

                if cursor.rowcount == 1:
                    return "inserted"

                existing = connection.execute(
                    """
                    SELECT record_json
                    FROM ingested_financial_records
                    WHERE provider = ?
                      AND namespace = ?
                      AND record_id = ?
                    """,
                    (
                        identity.provider,
                        identity.namespace,
                        identity.record_id,
                    ),
                ).fetchone()

                if existing is None:
                    raise RuntimeError(
                        "Record identity disappeared during ingestion"
                    )

                if existing[0] == payload:
                    return "duplicate"

                return "conflict"
            
    def record_batch(
    self,
    records: tuple[CanonicalFinancialRecord, ...],
) -> tuple[int, int, int]:
        """Atomically persist a batch, rejecting conflicting identities."""
        inserted = 0
        duplicates = 0
        conflicts = 0
        with closing(sqlite3.connect(self.database_path)) as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                # First, validate every record against persisted records.
                seen = {}
                for record in records:
                    identity = record.identity
                    payload = serialize_record(record)
                    if identity in seen:
                        if seen[identity] != payload:
                            conflicts += 1
                        else:
                            duplicates += 1
                        continue
                    seen[identity] = payload
                    existing = connection.execute(
                        """
                        SELECT record_json
                        FROM ingested_financial_records
                        WHERE provider = ?
                          AND namespace = ?
                          AND record_id = ?
                        """,
                        (
                            identity.provider,
                            identity.namespace,
                            identity.record_id,
                        ),
                    ).fetchone()
                    if existing is not None:
                        if existing[0] != payload:
                            conflicts += 1
                        else:
                            duplicates += 1
                if conflicts:
                    connection.rollback()
                    return (0, 0, conflicts)
                # Only insert records after all conflicts are ruled out.
                for record in records:
                    identity = record.identity
                    cursor = connection.execute(
                        """
                        INSERT INTO ingested_financial_records (
                            provider, namespace, record_id, record_json
                        )
                        VALUES (?, ?, ?, ?)
                        ON CONFLICT (provider, namespace, record_id)
                        DO NOTHING
                        """,
                        (
                            identity.provider,
                            identity.namespace,
                            identity.record_id,
                            serialize_record(record),
                        ),
                    )
                    if cursor.rowcount == 1:
                        inserted += 1
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return (inserted, duplicates, 0)