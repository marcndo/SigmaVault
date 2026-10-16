from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from uuid import UUID


class PaymentStatus(str, Enum):
    APPROVED = "approved"
    BROADCASTING = "broadcasting"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass(frozen=True)
class PaymentAuthorization:
    payment_id: UUID
    sender: str
    recipient: str
    amount: Decimal
    chain_id: int
    status: PaymentStatus

    def __post_init__(self) -> None:
        if not self.amount.is_finite() or self.amount <= 0:
            raise ValueError("Payment amount must be positive")

        if self.chain_id != 5042002:
            raise ValueError("Only Arc Testnet is supported")

        if self.sender.lower() == self.recipient.lower():
            raise ValueError("Sender and recipient must differ")