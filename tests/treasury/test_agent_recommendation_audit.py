import sqlite3
from datetime import date

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.beancount_audit_journal import (
    BeancountAuditJournal,
)
from sigmavault.treasury.decision_service import (
    TreasuryDecisionService,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)
from sigmavault.treasury.treasury_agent import (
    TreasuryRecommendation,
)


def test_actual_agent_recommendation_is_signed_and_journaled(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    journal_path = tmp_path / "treasury_decisions.beancount"
    database_path = tmp_path / "audit.sqlite3"

    recommendation = TreasuryRecommendation(
        action="preserve_liquidity",
        explanation=(
            "Execution is not eligible because financial evidence "
            "is unverified. Human review is required."
        ),
        requires_human_review=True,
    )

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        journal = BeancountAuditJournal(
            path=journal_path,
            public_key=public_key,
        )

        service = TreasuryDecisionService(
            repository=repository,
            private_key=private_key,
            policy_version="pilot-v1",
            journal=journal,
        )

        record = service.record_recommendation(
            decision_id="AGENT-001",
            recommendation=recommendation,
            event_date=date(2026, 10, 15),
        )

        connection.commit()

        stored = repository.get_by_decision_id("AGENT-001")

        assert stored == record

        assert record.payload.outcome == "deferred"
        assert recommendation.action in record.payload.explanation
        assert recommendation.explanation in record.payload.explanation

        journal_content = journal_path.read_text(encoding="utf-8")

        assert record.journal_entry in journal_content
        assert "AGENT-001" in journal_content

        assert verify_complete_decision_audit(
            payload=stored.payload,
            journal_entry=stored.journal_entry,
            signature=stored.signature,
            public_key=public_key,
        )

    finally:
        connection.close()