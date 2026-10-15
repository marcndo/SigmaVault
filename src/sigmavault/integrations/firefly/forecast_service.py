from datetime import date

from sigmavault.integrations.firefly.adapter import (
    parse_firefly_historical_record,
)
from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.treasury.forecasting import (
    ExpenseForecast,
    forecast_recurring_expenses,
)


def generate_firefly_expense_forecasts(
    client: FireflyClient,
    account_id: int,
    as_of: date,
    months_required: int = 6,
) -> list[ExpenseForecast]:
    """Generate recurring-expense forecasts from Firefly history."""

    groups = client.get_account_transactions(account_id)

    historical_records = [
        parse_firefly_historical_record(group)
        for group in groups
    ]

    return forecast_recurring_expenses(
        records=historical_records,
        as_of=as_of,
        months_required=months_required,
    )