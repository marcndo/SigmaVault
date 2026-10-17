from dataclasses import dataclass
from sigmavault.pipeline.repository import SQLiteIngestionRepository
from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)
from sigmavault.pipeline.source import FinancialDataSource


@dataclass(frozen=True)
class PipelineResult:
    records: tuple[CanonicalFinancialRecord, ...]
    duplicate_count: int
    source_count: int
    
    
@dataclass(frozen=True)
class IngestionResult:
    inserted_count: int
    duplicate_count: int
    conflict_count: int
    source_count: int


class FinancialDataPipeline:
    """Read-only ingestion pipeline shared by all source adapters."""

    def process(
        self,
        source: FinancialDataSource,
    ) -> PipelineResult:
        incoming = source.fetch_records()
        seen: dict[SourceRecordIdentity, CanonicalFinancialRecord] = {}
        accepted: list[CanonicalFinancialRecord] = []

        duplicate_count = 0
        for record in incoming:
            if not isinstance(record, CanonicalFinancialRecord):
                raise TypeError(
                    "Data source returned a non-canonical record"
                )
        
            if record.identity in seen:
                if seen[record.identity] != record:
                    raise ValueError(
                        "Conflicting records share the same source identity"
                    )
        
                duplicate_count += 1
                continue
        
            seen[record.identity] = record
            accepted.append(record)
        
        return PipelineResult(
            records=tuple(accepted),
            duplicate_count=duplicate_count,
            source_count=len(incoming),
        )
        
    def ingest(
        self,
        source: FinancialDataSource,
        repository: SQLiteIngestionRepository,
    ) -> IngestionResult:
        """Persist records after explicit ingestion approval."""

        preview = self.process(source)

        inserted, persisted_duplicates, conflicts = repository.record_batch(
            preview.records
        )

        return IngestionResult(
            inserted_count=inserted,
            duplicate_count=(
                preview.duplicate_count + persisted_duplicates
            ),
            conflict_count=conflicts,
            source_count=preview.source_count,
        )