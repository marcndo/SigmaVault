from decimal import Decimal

import pytest

from sigmavault.treasury.ingestion import load_financial_records


HEADER = (
    "id,description,category,subcategory,amount,currency,"
    "type,transaction_date,due_date,status,source,project_id,location\n"
)

ROW = (
    "OBS-001,Office rent,Office Bills,Office rent,"
    "100000,XAF,expense,,2026-09-01,unverified,forecast,,Yaounde\n"
)


def test_loads_financial_record(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text(HEADER + ROW, encoding="utf-8")

    records = load_financial_records(path)

    assert len(records) == 1
    assert records[0].record_id == "OBS-001"
    assert records[0].amount == Decimal("100000")
    assert records[0].currency == "XAF"
    assert records[0].status == "unverified"
    assert records[0].transaction_date is None


def test_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text(HEADER + ROW + ROW, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate"):
        load_financial_records(path)


def test_rejects_invalid_amount(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text(
        HEADER + ROW.replace("100000", "invalid"),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="amount"):
        load_financial_records(path)


def test_preserves_unverified_status(tmp_path):
    path = tmp_path / "records.csv"
    path.write_text(HEADER + ROW, encoding="utf-8")

    record = load_financial_records(path)[0]

    assert record.status == "unverified"
    assert record.source == "forecast"