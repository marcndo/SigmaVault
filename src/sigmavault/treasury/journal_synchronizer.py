import os
import sqlite3
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def synchronize_journal(
    connection: sqlite3.Connection,
    journal_path: str | Path,
    public_key: Ed25519PublicKey,
) -> int:
    """Build a verified journal from committed signed records.

    Existing journal content is never silently overwritten.
    """

    path = Path(journal_path)
    repository = SQLiteSignedDecisionRepository(connection)

    rows = connection.execute(
        """
        SELECT decision_id
        FROM signed_decision_records
        ORDER BY rowid
        """
    ).fetchall()

    parts = []

    for (decision_id,) in rows:
        record = repository.get_by_decision_id(decision_id)

        if record is None:
            raise RuntimeError(
                f"Missing signed record: {decision_id}"
            )

        if not verify_complete_decision_audit(
            payload=record.payload,
            journal_entry=record.journal_entry,
            signature=record.signature,
            public_key=public_key,
        ):
            raise ValueError(
                f"Invalid signed record: {decision_id}"
            )

        entry = record.journal_entry

        if not entry.endswith("\n"):
            entry += "\n"

        parts.append(entry + "\n")

    expected = "".join(parts)

    if path.exists():
        actual = path.read_text(encoding="utf-8")

        if actual == expected:
            return len(rows)

        valid_prefixes = {""}
        prefix = ""

        for part in parts:
            prefix += part
            valid_prefixes.add(prefix)

        if actual not in valid_prefixes:
            raise RuntimeError(
                "Existing Beancount journal is not a valid signed "
                "record prefix; manual reconciliation required"
            )

    path.parent.mkdir(parents=True, exist_ok=True)

    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".sigmavault-journal-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(expected)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, path)

    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return len(rows)