from typing import Protocol

from sigmavault.pipeline.models import CanonicalFinancialRecord


class FinancialDataSource(Protocol):
    """Contract implemented by every financial data source."""

    def fetch_records(self) -> list[CanonicalFinancialRecord]:
        ...