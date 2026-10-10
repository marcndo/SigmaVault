from dataclasses import FrozenInstanceError
from decimal import Decimal
import pytest
from datetime import date, timedelta
from sigmavault.treasury.domain import (Money,
                                        Obligation,
                                        ObligationSource, 
                                        PolicyTreasury,
                                        LiquidityPosition,
                                        LiquidityStatus)


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
        source = ObligationSource.CONFIRMED,    
    )
    assert obligation.amount == Money(Decimal("5200.00"),"USD")
    assert obligation.due_date == date(2026, 10, 6)
    assert obligation.source == ObligationSource.CONFIRMED
    
def test_obligation_is_immutable():
        obligation = Obligation(
        amount = Money(Decimal("5200.00"),"USD"),
        due_date = date(2026,10, 6),
        source = ObligationSource.CONFIRMED,
        )
        with pytest.raises(FrozenInstanceError):
            obligation.due_date = date(2026, 10, 10)
        
    
def test_treasury_policy_can_be_created():
    policy = PolicyTreasury(
      planning_horizon = timedelta(days=14),
      minimum_cash_buffer = Money(Decimal("8000.00"),"USD"),   
    )
    assert policy.planning_horizon == timedelta(days=14)
    assert policy.minimum_cash_buffer == Money(Decimal("8000.00"),"USD")
    

def test_treasury_policy_rejects_none_positive_planning_horizon():
    with pytest.raises(ValueError):
        PolicyTreasury(
      planning_horizon = -timedelta(days=14),
      minimum_cash_buffer = Money(Decimal("8000.00"),"USD"),   
    )
    

def test_treasury_policy_rejects_negative_cash_butter():
    with pytest.raises(ValueError):
        PolicyTreasury(
      planning_horizon = timedelta(days=14),
      minimum_cash_buffer = Money(Decimal("-10.00"),"USD"),   
    )

def test_treasury_policy_is_immutable():
    with pytest.raises(FrozenInstanceError):
        policy = PolicyTreasury(
      planning_horizon = timedelta(days=14),
      minimum_cash_buffer = Money(Decimal("8000.00"),"USD"),   
    )
        policy.planning_horizon = timedelta(days=20)

def test_liquidity_position_can_be_created():
    position = LiquidityPosition(
        available_cash = Money(Decimal("40000"),"USD"),
        required_liquidity = Money(Decimal("22000"),"USD"),
        minimum_cash_buffer = Money(Decimal("8000"),"USD"),
        deployable_surplus = Money(Decimal("10000"),"USD"),
        liquidity_shortfall = Money(Decimal("0"),"UDS"),
        status = LiquidityStatus.SUFFICIENT     
    )
    assert position.deployable_surplus == Money(Decimal("10000"),"USD")
    assert position.status is LiquidityStatus.SUFFICIENT
    
def test_liquidity_position_is_immutable():
        position = LiquidityPosition(
        available_cash = Money(Decimal("25000"),"USD"),
        required_liquidity = Money(Decimal("10000"),"USD"),
        minimum_cash_buffer = Money(Decimal("8000"),"USD"),
        deployable_surplus = Money(Decimal("7000"),"USD"),
        liquidity_shortfall = Money(Decimal("0"),"UDS"),
        status = LiquidityStatus.INSUFFICIENT
        )
        with pytest.raises(FrozenInstanceError):
            position.status = LiquidityStatus.SUFFICIENT

    
    