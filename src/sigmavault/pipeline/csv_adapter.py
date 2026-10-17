from pathlib import Path

from sigmavault.pipeline.models import (
    CanonicalFinancialRecord,
    SourceRecordIdentity,
)
from sigmavault.treasury.ingestion import load_financial_records


class CSVSourceAdapter:
    """Convert validated CSV records into canonical financial records."""

    def __init__(self, path: Path, namespace: str) -> None:
        self.path = Path(path)

        if not isinstance(namespace, str) or not namespace.strip():
            raise ValueError("CSV namespace must be nonempty")

        self.namespace = namespace.strip()

    def fetch_records(self) -> list[CanonicalFinancialRecord]:
        records = load_financial_records(self.path)

        return [
            CanonicalFinancialRecord(
                identity=SourceRecordIdentity(
                    provider="csv",
                    namespace=self.namespace,
                    record_id=record.record_id,
                ),
                description=record.description,
                category=record.category,
                subcategory=record.subcategory,
                amount=record.amount,
                currency=record.currency,
                direction=record.record_type,
                transaction_date=record.transaction_date,
                due_date=record.due_date,
                status=record.status,
                source=record.source,
                project_id=record.project_id,
                location=record.location,
            )
            for record in records
        ]