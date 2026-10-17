from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class SourceRecordIdentity:
    provider: str
    namespace: str
    record_id: str

    def __post_init__(self) -> None:
        for name in ("provider", "namespace", "record_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")


@dataclass(frozen=True)
class CanonicalFinancialRecord:
    identity: SourceRecordIdentity
    description: str
    category: str
    subcategory: str
    amount: Decimal
    currency: str
    direction: str
    transaction_date: date | None
    due_date: date | None
    status: str
    source: str
    project_id: str = ""
    location: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("amount must be Decimal")

        if not self.amount.is_finite() or self.amount <= 0:
            raise ValueError("amount must be positive and finite")

        if not isinstance(self.currency, str) or not self.currency.strip():
            raise ValueError("currency must be nonempty")

        if self.direction not in {"income", "expense"}:
            raise ValueError("unsupported direction")

        if self.status not in {
            "paid", "unpaid", "cancelled", "unverified"
        }:
            raise ValueError("unsupported status")

        if self.source not in {"confirmed", "forecast"}:
            raise ValueError("unsupported source")

        if self.status == "paid" and self.transaction_date is None:
            raise ValueError("paid record requires transaction date")

        if self.status == "unpaid" and self.transaction_date is not None:
            raise ValueError("unpaid record cannot have transaction date")