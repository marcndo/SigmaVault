from decimal import Decimal
from unittest.mock import Mock
import pytest

from sigmavault.integrations.firefly.ingestion_service import (
    load_firefly_forecasts,
)


def test_load_firefly_forecasts_converts_transactions():
    client = Mock()

    client.get_account_transactions.return_value = [
        {
            "id": "101",
            "attributes": {
                "transactions": [
                    {
                        "type": "withdrawal",
                        "amount": "25000",
                        "currency_code": "XAF",
                    }
                ]
            },
        },
        {
            "id": "102",
            "attributes": {
                "transactions": [
                    {
                        "type": "deposit",
                        "amount": "100000",
                        "currency_code": "XAF",
                    }
                ]
            },
        },
    ]

    transactions = load_firefly_forecasts(
        client=client,
        account_id=17,
    )

    client.get_account_transactions.assert_called_once_with(17)

    assert len(transactions) == 2

    assert transactions[0].transaction_id == "101"
    assert transactions[0].amount == Decimal("25000")
    assert transactions[0].direction == "expense"
    assert transactions[0].status == "forecast"

    assert transactions[1].transaction_id == "102"
    assert transactions[1].amount == Decimal("100000")
    assert transactions[1].direction == "income"
    assert transactions[1].status == "forecast"
    
    
def test_load_firefly_forecasts_returns_empty_list():
    client = Mock()
    client.get_account_transactions.return_value = []

    transactions = load_firefly_forecasts(
        client=client,
        account_id=17,
    )

    client.get_account_transactions.assert_called_once_with(17)

    assert transactions == []
    
def test_load_firefly_forecasts_rejects_invalid_batch():
    client = Mock()

    client.get_account_transactions.return_value = [
        {
            "id": "101",
            "attributes": {
                "transactions": [
                    {
                        "type": "withdrawal",
                        "amount": "25000",
                        "currency_code": "XAF",
                    }
                ]
            },
        },
        {
            "id": "102",
            "attributes": {
                "transactions": [
                    {
                        "type": "withdrawal",
                        "amount": "invalid",
                        "currency_code": "XAF",
                    }
                ]
            },
        },
        {
            "id": "103",
            "attributes": {
                "transactions": [
                    {
                        "type": "deposit",
                        "amount": "100000",
                        "currency_code": "XAF",
                    }
                ]
            },
        },
    ]

    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction amount",
    ):
        load_firefly_forecasts(
            client=client,
            account_id=17,
        )
        
        
def test_load_firefly_forecasts_propagates_client_failure():
    client = Mock()

    client.get_account_transactions.side_effect = RuntimeError(
        "Firefly API unavailable"
    )

    with pytest.raises(
        RuntimeError,
        match="Firefly API unavailable",
    ):
        load_firefly_forecasts(
            client=client,
            account_id=17,
        )

    client.get_account_transactions.assert_called_once_with(17)