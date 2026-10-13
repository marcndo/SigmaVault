from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.integrations.firefly.adapter import (
    parse_firefly_transaction,
)
from sigmavault.treasury.domain import FinancialTransaction


def load_firefly_forecasts(
    client: FireflyClient,
    account_id: int,
) -> list[FinancialTransaction]:
    """Load Firefly transaction groups as forecast transactions."""

    groups = client.get_account_transactions(account_id)

    transactions = []

    for group in groups:
        transaction = parse_firefly_transaction(
            group,
            status="forecast",
        )
        transactions.append(transaction)

    return transactions