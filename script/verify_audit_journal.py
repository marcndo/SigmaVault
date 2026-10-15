import os
import sqlite3
import sys
from pathlib import Path

from beancount.loader import load_file
from beancount.core.data import Event

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


DATABASE_PATH = Path(
    os.getenv(
        "SIGMAVAULT_DATABASE_PATH",
        "data/sigmavault_pilot.sqlite3",
    )
)

JOURNAL_PATH = Path(
    os.getenv(
        "SIGMAVAULT_AUDIT_JOURNAL_PATH",
        "data/treasury_decisions.beancount",
    )
)

def verify_complete_journal(
    connection: sqlite3.Connection,
    public_key: Ed25519PublicKey,
) -> bool:
    """Verify that the journal exactly matches signed SQLite records."""

    rows = connection.execute(
        """
        SELECT decision_id
        FROM signed_decision_records
        ORDER BY rowid
        """
    ).fetchall()

    repository = SQLiteSignedDecisionRepository(connection)

    expected_parts = []

    for (decision_id,) in rows:
        record = repository.get_by_decision_id(decision_id)

        if record is None:
            print(f"FAIL: Missing signed record: {decision_id}")
            return False

        if not verify_complete_decision_audit(
            payload=record.payload,
            journal_entry=record.journal_entry,
            signature=record.signature,
            public_key=public_key,
        ):
            print(f"FAIL: Invalid signed record: {decision_id}")
            return False

        entry = record.journal_entry

        if not entry.endswith("\n"):
            entry += "\n"

        expected_parts.append(entry + "\n")

    expected_journal = "".join(expected_parts)

    actual_journal = JOURNAL_PATH.read_text(encoding="utf-8")

    if actual_journal != expected_journal:
        print(
            "FAIL: Beancount journal differs from signed SQLite records"
        )
        return False

    print(
        f"PASS: Complete journal matches {len(rows)} signed SQLite records"
    )

    return True


def verify_journal() -> bool:
    if not JOURNAL_PATH.exists():
        print("FAIL: Beancount journal does not exist")
        return False

    if not DATABASE_PATH.exists():
        print("FAIL: Audit database does not exist")
        return False

    entries, errors, _ = load_file(str(JOURNAL_PATH))

    if errors:
        print("FAIL: Beancount parsing errors")
        for error in errors:
            print(error)
        return False

    events = [
        entry
        for entry in entries
        if isinstance(entry, Event)
        and entry.type == "SigmaVaultDecision"
    ]

    if not events:
        print("FAIL: No SigmaVault decision events found")
        return False

    public_key_path = Path(
        os.getenv(
            "SIGMAVAULT_AUDIT_PUBLIC_KEY_PATH",
            "data/keys/audit_verification_public.pem",
        )
    )

    public_key = serialization.load_pem_public_key(
        public_key_path.read_bytes()
    )
    
    if not isinstance(public_key, Ed25519PublicKey):
        raise ValueError("Verification key must be Ed25519")
    
    connection = sqlite3.connect(DATABASE_PATH)
    
    try:
        repository = SQLiteSignedDecisionRepository(connection)

        seen_ids = set()

        for event in events:
            decision_id = event.meta.get("decision_id")

            if not decision_id:
                print("FAIL: Event missing decision ID")
                return False

            if decision_id in seen_ids:
                print(f"FAIL: Duplicate decision ID: {decision_id}")
                return False

            seen_ids.add(decision_id)

            record = repository.get_by_decision_id(decision_id)

            if record is None:
                print(f"FAIL: Missing database record: {decision_id}")
                return False

            if record.payload.event_date != event.date:
                print(f"FAIL: Date mismatch: {decision_id}")
                return False

            if record.payload.outcome != event.meta.get("outcome"):
                print(f"FAIL: Outcome mismatch: {decision_id}")
                return False

            if record.payload.explanation != event.meta.get("explanation"):
                print(f"FAIL: Explanation mismatch: {decision_id}")
                return False

            if not verify_complete_decision_audit(
                payload=record.payload,
                journal_entry=record.journal_entry,
                signature=record.signature,
                public_key=public_key,
            ):
                print(f"FAIL: Signature or journal verification: {decision_id}")
                return False

            print(f"PASS: {decision_id}")

        if not verify_complete_journal(
            connection=connection,
            public_key=public_key,
        ):
            return False
        
        print(f"\nVerified {len(events)} signed decision events.")
        return True

    finally:
        connection.close()


if __name__ == "__main__":
    try:
        successful = verify_journal()
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        successful = False

    sys.exit(0 if successful else 1)