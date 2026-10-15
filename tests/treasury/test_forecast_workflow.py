import sqlite3
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.decision_service import TreasuryDecisionService
from sigmavault.treasury.domain import Money
from sigmavault.treasury.forecast_workflow import (
    run_forecast_decision_workflow,
)
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def test_firefly_forecast_to_persisted_signed_decision(tmp_path):
    client = Mock()

    client.get_account_transactions.return_value = [
        {
            "id": str(month),
            "attributes": {
                "transactions": [
                    {
                        "type": "withdrawal",
                        "amount": "25000",
                        "currency_code": "XAF",
                        "category_name": "Office Bills",
                        "description": "Internet",
                        "date": f"2026-{month:02d}-15",
                    }
                ]
            },
        }
        for month in range(4, 10)
    ]

    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    database_path = tmp_path / "treasury.sqlite3"

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        service = TreasuryDecisionService(
            repository=repository,
            private_key=private_key,
            policy_version="1.0.0",
        )

        created_record = run_forecast_decision_workflow(
            client=client,
            account_id=17,
            as_of=date(2026, 10, 1),
            available_cash=Money(Decimal("100000"), "XAF"),
            minimum_buffer=Money(Decimal("20000"), "XAF"),
            planning_horizon=timedelta(days=30),
            decision_id="DEC-FIREFLY-001",
            decision_service=service,
        )

        connection.commit()

    finally:
        connection.close()

    connection = sqlite3.connect(database_path)

    try:
        repository = SQLiteSignedDecisionRepository(connection)

        stored_record = repository.get_by_decision_id(
            "DEC-FIREFLY-001"
        )

    finally:
        connection.close()

    client.get_account_transactions.assert_called_once_with(17)

    assert stored_record == created_record
    assert stored_record.payload.outcome == "deferred"
    assert "55000 XAF" in stored_record.payload.explanation

    assert verify_complete_decision_audit(
        payload=stored_record.payload,
        journal_entry=stored_record.journal_entry,
        signature=stored_record.signature,
        public_key=public_key,
    ) is True