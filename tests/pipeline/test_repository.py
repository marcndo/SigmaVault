from dataclasses import replace
from datetime import date
from decimal import Decimal

from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)
from sigmavault.pipeline.repository import SQLiteIngestionRepository


def make_record(
    provider="csv",
    namespace="test-account",
    record_id="101",
):
    return CanonicalFinancialRecord(
        identity=SourceRecordIdentity(
            provider=provider,
            namespace=namespace,
            record_id=record_id,
        ),
        description="Office supplies",
        category="Operations",
        subcategory="Stationery",
        amount=Decimal("25000"),
        currency="XAF",
        direction="expense",
        transaction_date=date(2026, 10, 1),
        due_date=None,
        status="paid",
        source="confirmed",
    )


def test_repository_persists_new_record(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")

    assert repository.record(make_record()) == "inserted"


def test_repository_detects_duplicate(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")
    record = make_record()

    assert repository.record(record) == "inserted"
    assert repository.record(record) == "duplicate"


def test_repository_detects_conflicting_record(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")

    original = make_record()
    changed = replace(original, amount=Decimal("30000"))

    assert repository.record(original) == "inserted"
    assert repository.record(changed) == "conflict"


def test_repository_survives_restart(tmp_path):
    database_path = tmp_path / "ingestion.db"
    record = make_record()

    first = SQLiteIngestionRepository(database_path)
    assert first.record(record) == "inserted"

    second = SQLiteIngestionRepository(database_path)
    assert second.record(record) == "duplicate"


def test_repository_distinguishes_sources(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")

    csv_record = make_record(provider="csv")
    firefly_record = make_record(provider="firefly")

    assert repository.record(csv_record) == "inserted"
    assert repository.record(firefly_record) == "inserted"


def test_repository_distinguishes_namespaces(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")

    first = make_record(namespace="account-a")
    second = make_record(namespace="account-b")

    assert repository.record(first) == "inserted"
    assert repository.record(second) == "inserted"
    
    
def test_record_batch_counts_repeated_new_identity_once(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")
    record = make_record()

    result = repository.record_batch((record, record))

    assert result == (1, 1, 0)

    assert repository.record(record) == "duplicate"