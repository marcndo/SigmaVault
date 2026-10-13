from decimal import Decimal
import pytest


from sigmavault.integrations.firefly.adapter import (
    parse_firefly_transaction,
)


def test_parse_firefly_forecast_withdrawal():
    firefly_group = {
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
    }

    transaction = parse_firefly_transaction(
        firefly_group,
        status="forecast",
    )

    assert transaction.transaction_id == "101"
    assert transaction.amount == Decimal("25000")
    assert transaction.currency == "XAF"
    assert transaction.status == "forecast"
    assert transaction.direction == "expense"
    
    
def test_parse_firefly_forecast_deposit():
    firefly_group = {
        "id": "102",
        "attributes": {
            "transactions": [
                {
                    "type": "deposit",
                    "amount": "150000",
                    "currency_code": "XAF",
                }
            ]
        },
    }

    transaction = parse_firefly_transaction(
        firefly_group,
        status="forecast",
    )

    assert transaction.transaction_id == "102"
    assert transaction.amount == Decimal("150000")
    assert transaction.currency == "XAF"
    assert transaction.status == "forecast"
    assert transaction.direction == "income"
    
    

@pytest.mark.parametrize(
    "invalid_type",
    [
        "transfer",
        "unknown",
        "",
        "WITHDRAWAL",
        None,
        123,
    ],
)
def test_parse_firefly_rejects_unsupported_transaction_type(
    invalid_type,
):
    firefly_group = {
        "id": "103",
        "attributes": {
            "transactions": [
                {
                    "type": invalid_type,
                    "amount": "100000",
                    "currency_code": "XAF",
                }
            ]
        },
    }

    with pytest.raises(
        ValueError,
        match="Unsupported Firefly transaction type",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
        
def test_parse_firefly_rejects_multiple_splits():
    firefly_group = {
        "id": "104",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": "100000",
                    "currency_code": "XAF",
                },
                {
                    "type": "withdrawal",
                    "amount": "50000",
                    "currency_code": "XAF",
                },
            ]
        },
    }

    with pytest.raises(
        ValueError,
        match="Firefly transaction group must contain exactly one split",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        

def test_parse_firefly_rejects_empty_transaction_group():
    firefly_group = {
        "id": "105",
        "attributes": {
            "transactions": []
        },
    }

    with pytest.raises(
        ValueError,
        match="Firefly transaction group must contain exactly one split",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
@pytest.mark.parametrize(
    "invalid_transactions",
    [
        None,
        {},
        "invalid",
        123,
        (),
    ],
)
def test_parse_firefly_rejects_invalid_transaction_collection(
    invalid_transactions,
):
    firefly_group = {
        "id": "106",
        "attributes": {
            "transactions": invalid_transactions,
        },
    }

    with pytest.raises(
        ValueError,
        match="Firefly transaction group must contain exactly one split",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
     
     
        
@pytest.mark.parametrize(
    "invalid_group",
    [
        {"id": "107"},
        {"id": "107", "attributes": {}},
        {"id": "107", "attributes": None},
        {"id": "107", "attributes": []},
    ],
)
def test_parse_firefly_rejects_missing_transaction_structure(
    invalid_group,
):
    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction group structure",
    ):
        parse_firefly_transaction(
            invalid_group,
            status="forecast",
        )
  
  
        
@pytest.mark.parametrize(
    "invalid_split",
    [
        None,
        {},
        [],
        "invalid",
        123,
    ],
)
def test_parse_firefly_rejects_invalid_transaction_split(
    invalid_split,
):
    firefly_group = {
        "id": "108",
        "attributes": {
            "transactions": [invalid_split],
        },
    }

    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction split structure",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
        
def test_parse_firefly_rejects_malformed_amount():
    firefly_group = {
        "id": "109",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": "invalid",
                    "currency_code": "XAF",
                }
            ]
        },
    }

    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction amount",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
        
        
@pytest.mark.parametrize(
    "invalid_amount",
    [
        25000,
        25000.75,
        None,
        True,
    ],
)
def test_parse_firefly_rejects_non_string_amount(
    invalid_amount,
):
    firefly_group = {
        "id": "110",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": invalid_amount,
                    "currency_code": "XAF",
                }
            ]
        },
    }

    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction amount",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
@pytest.mark.parametrize(
    "invalid_amount",
    [
        "NaN",
        "Infinity",
        "-Infinity",
        "-25000",
    ],
)
def test_parse_firefly_rejects_non_finite_or_negative_amount(
    invalid_amount,
):
    firefly_group = {
        "id": "111",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": invalid_amount,
                    "currency_code": "XAF",
                }
            ]
        },
    }

    with pytest.raises(ValueError):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
        
def test_parse_firefly_rejects_missing_group_id():
    firefly_group = {
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": "25000",
                    "currency_code": "XAF",
                }
            ]
        }
    }

    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction group ID",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
@pytest.mark.parametrize(
    "invalid_id",
    [
        None,
        123,
        "",
        "   ",
        [],
        {},
    ],
)
def test_parse_firefly_rejects_invalid_group_id(
    invalid_id,
):
    firefly_group = {
        "id": invalid_id,
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": "25000",
                    "currency_code": "XAF",
                }
            ]
        },
    }

    with pytest.raises(
        ValueError,
        match="Invalid Firefly transaction group ID",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )
        
@pytest.mark.parametrize(
    "invalid_type",
    [
        [],
        {},
    ],
)
def test_parse_firefly_rejects_unhashable_transaction_type(
    invalid_type,
):
    firefly_group = {
        "id": "112",
        "attributes": {
            "transactions": [
                {
                    "type": invalid_type,
                    "amount": "25000",
                    "currency_code": "XAF",
                }
            ]
        },
    }

    with pytest.raises(
        ValueError,
        match="Unsupported Firefly transaction type",
    ):
        parse_firefly_transaction(
            firefly_group,
            status="forecast",
        )