import csv
from io import StringIO

from fastapi.testclient import TestClient

from sigmavault.web.app import app
from sigmavault.treasury.ingestion import REQUIRED_COLUMNS


client = TestClient(app)


def test_preview_valid_csv_returns_records():
    csv_buffer = StringIO()

    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=sorted(REQUIRED_COLUMNS),
    )

    writer.writeheader()

    writer.writerow(
        {
            "id": "OBSEC-001",
            "description": "Office rent",
            "category": "Operations",
            "subcategory": "Rent",
            "amount": "150000",
            "currency": "XAF",
            "type": "expense",
            "transaction_date": "2026-09-05",
            "due_date": "",
            "status": "paid",
            "source": "confirmed",
            "project_id": "",
            "location": "Douala",
        }
    )

    response = client.post(
        "/api/csv/preview",
        files={
            "file": (
                "obsec.csv",
                csv_buffer.getvalue().encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["valid"] is True
    assert data["record_count"] == 1
    assert data["records"][0]["record_id"] == "OBSEC-001"
    assert data["records"][0]["amount"] == "150000"
    
    
def test_preview_rejects_missing_required_columns():
    csv_content = (
        "id,description,amount,currency\n"
        "OBSEC-001,Office rent,150000,XAF\n"
    )

    response = client.post(
        "/api/csv/preview",
        files={
            "file": (
                "obsec.csv",
                csv_content.encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 422

    data = response.json()

    assert "missing required columns" in data["detail"].lower()
    
    
import pytest


@pytest.mark.parametrize(
    "invalid_amount",
    ["-150000", "0", "NaN", "Infinity", "abc"],
)
def test_preview_rejects_invalid_amounts(invalid_amount):
    csv_buffer = StringIO()

    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=sorted(REQUIRED_COLUMNS),
    )

    writer.writeheader()

    writer.writerow(
        {
            "id": "OBSEC-001",
            "description": "Office rent",
            "category": "Operations",
            "subcategory": "Rent",
            "amount": invalid_amount,
            "currency": "XAF",
            "type": "expense",
            "transaction_date": "2026-09-05",
            "due_date": "",
            "status": "paid",
            "source": "confirmed",
            "project_id": "",
            "location": "Douala",
        }
    )

    response = client.post(
        "/api/csv/preview",
        files={
            "file": (
                "obsec.csv",
                csv_buffer.getvalue().encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 422
    assert "invalid amount" in response.json()["detail"].lower()
    
    
def test_preview_rejects_duplicate_transaction_ids():
    csv_buffer = StringIO()

    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=sorted(REQUIRED_COLUMNS),
    )

    writer.writeheader()

    base_record = {
        "id": "OBSEC-001",
        "description": "Office rent",
        "category": "Operations",
        "subcategory": "Rent",
        "amount": "150000",
        "currency": "XAF",
        "type": "expense",
        "transaction_date": "2026-09-05",
        "due_date": "",
        "status": "paid",
        "source": "confirmed",
        "project_id": "",
        "location": "Douala",
    }

    writer.writerow(base_record)
    writer.writerow(base_record)

    response = client.post(
        "/api/csv/preview",
        files={
            "file": (
                "obsec.csv",
                csv_buffer.getvalue().encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 422
    assert "duplicate ID" in response.json()["detail"]
    
def test_preview_rejects_oversized_csv():
    oversized_content = b"x" * (5 * 1024 * 1024 + 1)

    response = client.post(
        "/api/csv/preview",
        files={
            "file": (
                "oversized.csv",
                oversized_content,
                "text/csv",
            )
        },
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()
    

def test_csv_preview_uses_unified_pipeline(monkeypatch):
    from sigmavault.web import app as web_app

    calls = []

    original_process = web_app.FinancialDataPipeline.process

    def tracking_process(self, source):
        calls.append(source)
        return original_process(self, source)

    monkeypatch.setattr(
        web_app.FinancialDataPipeline,
        "process",
        tracking_process,
    )

    csv_buffer = StringIO()

    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=sorted(REQUIRED_COLUMNS),
    )

    writer.writeheader()

    writer.writerow(
        {
            "id": "OBSEC-001",
            "description": "Office rent",
            "category": "Operations",
            "subcategory": "Rent",
            "amount": "150000",
            "currency": "XAF",
            "type": "expense",
            "transaction_date": "2026-09-05",
            "due_date": "",
            "status": "paid",
            "source": "confirmed",
            "project_id": "",
            "location": "Douala",
        }
    )

    response = client.post(
        "/api/csv/preview",
        files={
            "file": (
                "obsec.csv",
                csv_buffer.getvalue().encode("utf-8"),
                "text/csv",
            )
        },
    )

    assert response.status_code == 200
    assert len(calls) == 1
    assert isinstance(calls[0], web_app.CSVSourceAdapter)