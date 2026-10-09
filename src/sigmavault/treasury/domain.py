from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from datetime import date, timedelta

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
    
@dataclass(frozen=True)
class PolicyTreasury:
    planning_horizon: timedelta
    minimum_cash_buffer: Money
    
    def __post_init__(self):
        if not isinstance(self.planning_horizon, timedelta):
            raise TypeError("planning_horizon must be a timedelta")
        
        if self.planning_horizon <= timedelta(0):
            raise ValueError("planning_horizon must be greater than zero")
        
        if not isinstance(self.minimum_cash_buffer, Money):
            raise TypeError("minimum_cash_buffer must be a Money instance")
        
        if self.minimum_cash_buffer.amount < Decimal("0"):
            raise ValueError("minimum_cash_buffer must be greater than zero")
            
        

    