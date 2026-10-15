from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class FireflyHistoricalRecord:
    record_id: str
    category: str
    subcategory: str
    record_type: str
    status: str
    due_date: date
    amount: Decimal
    currency: str