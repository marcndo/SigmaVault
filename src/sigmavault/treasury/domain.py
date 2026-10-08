from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from datetime import date

@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str
    
    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("amount must be a Decimal")
        
        if not self.currency:
            raise ValueError("currency must not be empty")
        
class ObligationSource(Enum):
    CONFIRMED = "confirmed"
    FORECAST = "forecast"
    
@dataclass(frozen=True)
class Obligation:
    amount: Money
    due_date: date
    source: ObligationSource
    