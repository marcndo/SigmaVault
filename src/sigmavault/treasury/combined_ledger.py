"""Build a verified, human-readable SigmaVault Beancount ledger."""

import sqlite3
from datetime import date
from pathlib import Path

from beancount.loader import load_string
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from sigmavault.pipeline.models import SourceRecordIdentity
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_financial_repository import (
    SQLiteSignedFinancialRepository,
)
from sigmavault.treasury.signed_financial_transaction import (
    verify_signed_financial_record,
)


def build_combined_ledger(
    *,
    connection: sqlite3.Connection,
    public_key: Ed25519PublicKey,
) -> str:
    """Reconstruct a ledger from independently verified signed records."""

    entries = []
    accounts = set()

    financial_repository = SQLiteSignedFinancialRepository(connection)
    decision_repository = SQLiteSignedDecisionRepository(connection)

    financial_rows = connection.execute(
        """
        SELECT provider, namespace, record_id
        FROM signed_financial_records
        ORDER BY rowid
        """
    ).fetchall()

    for provider, namespace, record_id in financial_rows:
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

        accounts.add(record.payload.asset_account)
        accounts.add(record.payload.counterparty_account)

        entries.append(
            (record.payload.transaction_date, record.journal_entry)
        )

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

    for decision_id in decision_ids:
        record = decision_repository.get_by_decision_id(decision_id)

        if record is None or not verify_complete_decision_audit(
            payload=record.payload,
            journal_entry=record.journal_entry,
            signature=record.signature,
            public_key=public_key,
        ):
            raise ValueError(
                f"Invalid signed treasury decision: {decision_id}"
            )

        entries.append(
            (record.payload.event_date, record.journal_entry)
        )

    # Stable chronological ordering.
    entries.sort(key=lambda item: item[0])

    if entries:
        opening_date = min(item[0] for item in entries)
    else:
        opening_date = date.today()

    header = [
        'option "title" "SigmaVault Treasury Ledger"',
        'option "operating_currency" "XAF"',
        "",
    ]

    for account in sorted(accounts):
        header.append(
            f"{opening_date.isoformat()} open {account} XAF"
        )

    if accounts:
        header.append("")

    header.extend([
        "; ============================================",
        "; VERIFIED FINANCIAL TRANSACTIONS AND",
        "; SIGNED AI TREASURY DECISIONS",
        "; ============================================",
        "",
    ])

    ledger = "\n".join(header)

    for _, entry in entries:
        ledger += entry.rstrip() + "\n\n"

    parsed_entries, errors, _ = load_string(ledger)

    if errors:
        raise ValueError(
            f"Generated Beancount ledger is invalid: {errors}"
        )

    return ledger


def write_combined_ledger(
    *,
    connection: sqlite3.Connection,
    public_key: Ed25519PublicKey,
    output_path: str | Path,
) -> Path:
    """Write a validated combined ledger to disk."""

    ledger = build_combined_ledger(
        connection=connection,
        public_key=public_key,
    )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ledger, encoding="utf-8")

    return output_path