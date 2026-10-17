from dataclasses import replace
from datetime import date
from decimal import Decimal

from sigmavault.pipeline.coordinator import FinancialDataPipeline
from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)
from sigmavault.pipeline.repository import SQLiteIngestionRepository


class FakeSource:
    def __init__(self, records):
        self.records = records

    def fetch_records(self):
        return self.records


def make_record(record_id="1", amount="25000"):
    return CanonicalFinancialRecord(
        identity=SourceRecordIdentity(
            provider="csv",
            namespace="obsec-test",
            record_id=record_id,
        ),
        description="Office supplies",
        category="Operations",
        subcategory="Stationery",
        amount=Decimal(amount),
        currency="XAF",
        direction="expense",
        transaction_date=date(2026, 10, 1),
        due_date=None,
        status="paid",
        source="confirmed",
    )


def test_ingest_persists_new_records(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")
    source = FakeSource([make_record("1"), make_record("2")])

    result = FinancialDataPipeline().ingest(source, repository)

    assert result.inserted_count == 2
    assert result.duplicate_count == 0
    assert result.conflict_count == 0
    assert result.source_count == 2


def test_repeated_ingestion_is_idempotent(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")
    source = FakeSource([make_record()])

    pipeline = FinancialDataPipeline()

    first = pipeline.ingest(source, repository)
    second = pipeline.ingest(source, repository)

    assert first.inserted_count == 1
    assert second.inserted_count == 0
    assert second.duplicate_count == 1


def test_ingest_detects_changed_financial_facts(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")
    pipeline = FinancialDataPipeline()

    pipeline.ingest(FakeSource([make_record()]), repository)

    changed = replace(make_record(), amount=Decimal("30000"))
    result = pipeline.ingest(FakeSource([changed]), repository)

    assert result.inserted_count == 0
    assert result.conflict_count == 1


def test_preview_does_not_write_to_repository(tmp_path):
    database_path = tmp_path / "ingestion.db"
    repository = SQLiteIngestionRepository(database_path)
    source = FakeSource([make_record()])

    pipeline = FinancialDataPipeline()

    preview = pipeline.process(source)
    ingestion = pipeline.ingest(source, repository)

    assert len(preview.records) == 1
    assert ingestion.inserted_count == 1


def test_ingest_counts_identical_duplicates_within_batch(tmp_path):
    repository = SQLiteIngestionRepository(tmp_path / "ingestion.db")
    record = make_record()

    result = FinancialDataPipeline().ingest(
        FakeSource([record, record]),
        repository,
    )

    assert result.source_count == 2
    assert result.inserted_count == 1
    assert result.duplicate_count == 1
    
    
def test_conflicting_batch_does_not_partially_commit(tmp_path):
    database_path = tmp_path / "ingestion.db"
    repository = SQLiteIngestionRepository(database_path)
    pipeline = FinancialDataPipeline()

    existing = make_record(record_id="existing", amount="10000")
    pipeline.ingest(FakeSource([existing]), repository)

    new_record = make_record(record_id="new", amount="20000")
    conflicting = make_record(record_id="existing", amount="30000")

    result = pipeline.ingest(
        FakeSource([new_record, conflicting]),
        repository,
    )

    assert result.inserted_count == 0
    assert result.conflict_count == 1

    retry = pipeline.ingest(FakeSource([new_record]), repository)

    assert retry.inserted_count == 1