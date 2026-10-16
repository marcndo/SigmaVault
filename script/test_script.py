from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from sigmavault.treasury.ingestion import load_financial_records
from sigmavault.treasury.forecasting import forecast_recurring_expenses
from sigmavault.treasury.assessment import assess_forecast_liquidity
from sigmavault.treasury.domain import Money


def main() -> None:
    # Development-only inputs, not verified OBSEC balances.
    as_of = date(2026, 10, 1)
    available_cash = Money(Decimal("500000"), "XAF")
    minimum_buffer = Money(Decimal("200000"), "XAF")
    planning_horizon = timedelta(days=30)

    # 1. Load financial records.
    records = load_financial_records(
        Path("data/obsec/financial_records.csv")
    )

    # 2. Forecast recurring expenses.
    forecasts = forecast_recurring_expenses(
        records,
        as_of=as_of,
    )

    # 3. Calculate liquidity.
    position = assess_forecast_liquidity(
        forecasts=forecasts,
        available_cash=available_cash,
        minimum_buffer=minimum_buffer,
        planning_horizon=planning_horizon,
        as_of=as_of,
    )

    # 4. Display results.
    print("\nSIGMAVAULT — DEVELOPMENT TREASURY ASSESSMENT")
    print("=" * 65)
    print(f"Assessment date: {as_of}")
    print(f"Historical records: {len(records)}")

    print("\nFORECASTED EXPENSES")
    print("-" * 65)

    for forecast in forecasts:
        print(
            f"{forecast.subcategory:<20} "
            f"{forecast.amount:>12,.0f} "
            f"{forecast.currency} "
            f"Due: {forecast.due_date}"
        )

    print("\nLIQUIDITY ASSESSMENT")
    print("-" * 65)

    print(
        f"Available cash:       "
        f"{position.available_cash.amount:>12,.0f} XAF"
    )
    print(
        f"Required liquidity:   "
        f"{position.required_liquidity.amount:>12,.0f} XAF"
    )
    print(
        f"Minimum cash buffer:  "
        f"{position.minimum_cash_buffer.amount:>12,.0f} XAF"
    )
    print(
        f"Deployable surplus:   "
        f"{position.deployable_surplus.amount:>12,.0f} XAF"
    )
    print(
        f"Liquidity shortfall:  "
        f"{position.liquidity_shortfall.amount:>12,.0f} XAF"
    )
    print(f"Liquidity status:     {position.status}")

    print("\nDEVELOPMENT DATA ONLY — NOT VERIFIED OBSEC FINANCIAL DATA")


if __name__ == "__main__":
    main()