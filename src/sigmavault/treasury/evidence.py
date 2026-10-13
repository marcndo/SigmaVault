from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class FinancialEvidence:
    evidence_id: str
    source: str
    transaction_id: str
    amount: Decimal
    currency: str
    direction: str
    settlement_status: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.evidence_id, str)
            or not self.evidence_id.strip()
        ):
            raise ValueError("Invalid evidence ID")

        if (
            not isinstance(self.source, str)
            or not self.source.strip()
        ):
            raise ValueError("Invalid evidence source")

        if (
            not isinstance(self.transaction_id, str)
            or not self.transaction_id.strip()
        ):
            raise ValueError("Invalid evidence transaction ID")

        if (
            not isinstance(self.amount, Decimal)
            or not self.amount.is_finite()
            or self.amount < 0
        ):
            raise ValueError("Invalid evidence amount")
        if self.currency != "XAF":
            raise ValueError("Invalid evidence currency")
        if self.direction not in ("income", "expense"):
            raise ValueError("Invalid evidence direction")
        if self.settlement_status not in (
            "pending",
            "settled",
            "failed",
        ):
            raise ValueError("Invalid evidence settlement status")