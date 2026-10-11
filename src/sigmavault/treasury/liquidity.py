
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from sigmavault.treasury.domain import (
    LiquidityPosition,
    LiquidityStatus,
    Money,
    Obligation,
    TreasuryPolicy,
)

def calculate_liquidity(
    available_cash: Money,
    obligations: Sequence[Obligation],
    policy: TreasuryPolicy,
    as_of: date,
) -> LiquidityPosition:
    """
    Calculate a business's protected liquidity position.

    Assumes obligations represent outstanding payments.
    Does not authorize or execute financial transactions.
    """

    if not isinstance(available_cash, Money):
        raise TypeError("available_cash must be Money")

    if not isinstance(policy, TreasuryPolicy):
        raise TypeError("policy must be TreasuryPolicy")

    if not isinstance(as_of, date):
        raise TypeError("as_of must be a date")

    if available_cash.amount < Decimal("0"):
        raise ValueError("available cash cannot be negative")

    currency = available_cash.currency

    if policy.minimum_cash_buffer.currency != currency:
        raise ValueError("cash buffer currency mismatch")

    horizon_end = as_of + policy.planning_horizon

    required_amount = Decimal("0")

    for item in obligations:
        if not isinstance(item, Obligation):
            raise TypeError(
                "all obligations must be Obligation instances"
            )

        if item.amount.currency != currency:
            raise ValueError("obligation currency mismatch")

        if item.amount.amount < Decimal("0"):
            raise ValueError("obligation amount cannot be negative")

        if item.due_date <= horizon_end:
            required_amount += item.amount.amount

    buffer_amount = policy.minimum_cash_buffer.amount

    net_amount = (
        available_cash.amount
        - required_amount
        - buffer_amount
    )

    surplus_amount = max(Decimal("0"), net_amount)
    shortfall_amount = max(Decimal("0"), -net_amount)

    status = (
        LiquidityStatus.SUFFICIENT
        if net_amount >= Decimal("0")
        else LiquidityStatus.INSUFFICIENT
    )

    return LiquidityPosition(
        available_cash=available_cash,
        required_liquidity=Money(required_amount, currency),
        minimum_cash_buffer=policy.minimum_cash_buffer,
        deployable_surplus=Money(surplus_amount, currency),
        liquidity_shortfall=Money(shortfall_amount, currency),
        status=status,
    )
