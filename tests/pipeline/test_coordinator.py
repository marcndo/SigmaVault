from datetime import date
from decimal import Decimal
from dataclasses import replace


import pytest

from sigmavault.pipeline.coordinator import FinancialDataPipeline
from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)


def make_record(provider="csv", record_id="101"):
    return CanonicalFinancialRecord(
        identity=SourceRecordIdentity(
            provider=provider,
            namespace="test-account",
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


class FakeSource:
    def __init__(self, records):
        self.records = records

    def fetch_records(self):
        return self.records


def test_pipeline_accepts_canonical_records():
    source = FakeSource([make_record()])

    result = FinancialDataPipeline().process(source)

    assert result.source_count == 1
    assert len(result.records) == 1
    assert result.duplicate_count == 0


def test_pipeline_deduplicates_same_source_identity():
    record = make_record()

    source = FakeSource([record, record])

    result = FinancialDataPipeline().process(source)

    assert result.source_count == 2
    assert len(result.records) == 1
    assert result.duplicate_count == 1


def test_pipeline_keeps_different_provider_identities():
    source = FakeSource([
        make_record(provider="csv"),
        make_record(provider="firefly"),
    ])

    result = FinancialDataPipeline().process(source)

    assert len(result.records) == 2
    assert result.duplicate_count == 0


def test_pipeline_rejects_noncanonical_records():
    source = FakeSource([{"id": "101"}])

    with pytest.raises(TypeError, match="non-canonical"):
        FinancialDataPipeline().process(source)


def test_pipeline_returns_immutable_record_collection():
    source = FakeSource([make_record()])

    result = FinancialDataPipeline().process(source)

    assert isinstance(result.records, tuple)
    
def test_pipeline_rejects_conflicting_duplicate_identity():
    original = make_record()
    changed = replace(original, amount=Decimal("30000"))

    source = FakeSource([original, changed])

    with pytest.raises(ValueError, match="Conflicting"):
        FinancialDataPipeline().process(source)