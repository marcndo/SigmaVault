from decimal import Decimal

import pytest

from sigmavault.pipeline.csv_adapter import CSVSourceAdapter


CSV_HEADER = (
    "id,description,category,subcategory,amount,currency,type,"
    "transaction_date,due_date,status,source,project_id,location\n"
)


def test_csv_adapter_produces_canonical_records(tmp_path):
    path = tmp_path / "transactions.csv"

    path.write_text(
        CSV_HEADER
        + "101,Office supplies,Operations,Stationery,25000,XAF,"
        "expense,2026-10-01,,paid,confirmed,P1,Douala\n",
        encoding="utf-8",
    )

    adapter = CSVSourceAdapter(
        path=path,
        namespace="test-cash-account",
    )

    records = adapter.fetch_records()

    assert len(records) == 1

    record = records[0]

    assert record.identity.provider == "csv"
    assert record.identity.namespace == "test-cash-account"
    assert record.identity.record_id == "101"

    assert record.amount == Decimal("25000")
    assert record.direction == "expense"
    assert record.status == "paid"
    assert record.source == "confirmed"
    assert record.project_id == "P1"
    assert record.location == "Douala"


def test_csv_adapter_rejects_invalid_namespace(tmp_path):
    with pytest.raises(ValueError, match="namespace"):
        CSVSourceAdapter(
            path=tmp_path / "transactions.csv",
            namespace="",
        )


def test_csv_adapter_propagates_validation_errors(tmp_path):
    path = tmp_path / "invalid.csv"

    path.write_text(
        CSV_HEADER
        + "101,Office supplies,Operations,Stationery,-25000,XAF,"
        "expense,2026-10-01,,paid,confirmed,P1,Douala\n",
        encoding="utf-8",
    )

    adapter = CSVSourceAdapter(
        path=path,
        namespace="test-cash-account",
    )

    with pytest.raises(ValueError, match="invalid amount"):
        adapter.fetch_records()


def test_csv_adapter_preserves_unpaid_obligation(tmp_path):
    path = tmp_path / "unpaid.csv"

    path.write_text(
        CSV_HEADER
        + "102,Internet bill,Utilities,Internet,15000,XAF,"
        "expense,,2026-11-01,unpaid,confirmed,P1,Douala\n",
        encoding="utf-8",
    )

    records = CSVSourceAdapter(
        path=path,
        namespace="test-cash-account",
    ).fetch_records()

    assert len(records) == 1
    assert records[0].transaction_date is None
    assert records[0].due_date.isoformat() == "2026-11-01"
    assert records[0].status == "unpaid"