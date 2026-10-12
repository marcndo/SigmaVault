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
class TreasuryPolicy:
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
   
class LiquidityStatus(Enum):
    SUFFICIENT = "sufficient" 
    INSUFFICIENT = "insufficient"
    
@dataclass(frozen=True)
class LiquidityPosition:
    available_cash: Money
    required_liquidity: Money
    minimum_cash_buffer: Money
    deployable_surplus: Money
    liquidity_shortfall: Money
    status : LiquidityStatus
    
            
@dataclass(frozen=True)
class FinancialTransaction:
    transaction_id: str
    amount: Decimal
    currency: str
    status: str
    
    
@dataclass(frozen=True)
class FinancialTransaction:
    transaction_id: str
    amount: Decimal
    currency: str
    status: str
    direction: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise TypeError("Transaction amount must be a Decimal")
    
        if not self.amount.is_finite():
            raise ValueError("Transaction amount must be finite")
    
        if self.amount < 0:
            raise ValueError("Transaction amount cannot be negative")
    
        if not isinstance(self.transaction_id, str):
            raise TypeError("Transaction ID must be a string")
    
        if not self.transaction_id.strip():
            raise ValueError("Transaction ID cannot be empty")
    
        if not isinstance(self.currency, str):
            raise TypeError("Transaction currency must be a string")

        if self.currency != "XAF":
           raise ValueError("Unsupported transaction currency")
        if not isinstance(self.status, str):
            raise TypeError("Transaction status must be a string")

        if self.status not in {"forecast", "actual"}:
            raise ValueError("Unsupported transaction status")
        if not isinstance(self.direction, str):
            raise TypeError("Transaction direction must be a string")

        if self.direction not in {"income", "expense"}:
            raise ValueError("Unsupported transaction direction")