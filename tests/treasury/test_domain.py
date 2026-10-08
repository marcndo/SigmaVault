from dataclasses import FrozenInstanceError
from decimal import Decimal
from sigmavault.treasury.domain import Money
import pytest
from datetime import date
from sigmavault.treasury.domain import Obligation

def test_money_can_be_created():
    money = Money(Decimal("100.00"), "USD")
    
    assert money.amount == Decimal("100.00")
    assert money.currency == "USD"
    
def test_money_rejects_non_decimal_amount():
    with pytest.raises(TypeError):
        Money(1000, "USD")
        
def test_money_rejects_empty_currency():
    with pytest.raises(ValueError):
        Money(Decimal("100.00"), "")
        
def test_equal_money_values_are_equal():
    first = Money(Decimal("100.00"), "USD")
    second = Money(Decimal("100.00"),"USD")
    assert first == second
    
    
def test_money_is_immutable():
    money = Money(Decimal("100.00"),"USD")
    with pytest.raises(FrozenInstanceError):
        money.amount = Decimal("23.00")
        
def test_obligation_can_be_created():
    obligation = Obligation(
        amount = Money(Decimal("5200.00"),"USD"),
        due_date = date(2026,10, 6),
        status = ObligationSource.CONFIRMED,    
    )
    assert obligation.amout == Decimal("5200.00","USD")
    assert obligation.due_date == date(2026, 10, 6)
    assert obligation.status == ObligationSource.CONFIRMED
    
def test_obligation_is_immutable():
        obligation = Obligation(
        amount = Money(Decimal("5200.00"),"USD"),
        due_date = date(2026,10, 6),
        status = ObligationSource.CONFIRMED,
        )
        with pytest.raises(FrozenInstanceError):
            assert obligation.due_date == date(2026, 10, 10)
        
    
    