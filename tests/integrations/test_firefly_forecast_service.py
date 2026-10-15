from datetime import date
from decimal import Decimal
from unittest.mock import Mock

from sigmavault.integrations.firefly.forecast_service import (
    generate_firefly_expense_forecasts,
)


def test_generate_firefly_expense_forecasts_from_six_months():
    client = Mock()

    amounts = [
        "20000",
        "22000",
        "21000",
        "23000",
        "24000",
        "25000",
    ]

    months = [4, 5, 6, 7, 8, 9]

    groups = []

    for index, (month, amount) in enumerate(
        zip(months, amounts),
        start=1,
    ):
        groups.append(
            {
                "id": str(index),
                "attributes": {
                    "transactions": [
                        {
                            "type": "withdrawal",
                            "amount": amount,
                            "currency_code": "XAF",
                            "category_name": "Office Bills",
                            "description": "Internet",
                            "date": f"2026-{month:02d}-15",
                        }
                    ]
                },
            }
        )

    client.get_account_transactions.return_value = groups

    forecasts = generate_firefly_expense_forecasts(
        client=client,
        account_id=17,
        as_of=date(2026, 10, 1),
    )

    client.get_account_transactions.assert_called_once_with(17)

    assert len(forecasts) == 1

    forecast = forecasts[0]

    assert forecast.category == "Office Bills"
    assert forecast.subcategory == "Internet"
    assert forecast.amount == Decimal("22500")
    assert forecast.currency == "XAF"
    assert forecast.due_date == date(2026, 10, 15)
    assert forecast.source == "forecast"
    assert forecast.supporting_record_ids == (
        "1", "2", "3", "4", "5", "6"
    )