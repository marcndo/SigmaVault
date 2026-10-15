from datetime import date
from decimal import Decimal

import pytest

from sigmavault.integrations.firefly.adapter import (
    parse_firefly_historical_record,
)


def make_firefly_group():
    return {
        "id": "101",
        "attributes": {
            "transactions": [
                {
                    "type": "withdrawal",
                    "amount": "25000",
                    "currency_code": "XAF",
                    "category_name": "Office Bills",
                    "description": "Internet",
                    "date": "2026-09-15",
                }
            ]
        },
    }


def test_parse_firefly_historical_record_preserves_forecasting_fields():
    record = parse_firefly_historical_record(
        make_firefly_group()
    )

    assert record.record_id == "101"
    assert record.category == "Office Bills"
    assert record.subcategory == "Internet"
    assert record.record_type == "expense"
    assert record.status == "unverified"
    assert record.due_date == date(2026, 9, 15)
    assert record.amount == Decimal("25000")
    assert record.currency == "XAF"


@pytest.mark.parametrize(
    "field",
    ["category_name", "description", "date"],
)
def test_parse_firefly_historical_record_rejects_missing_fields(field):
    group = make_firefly_group()
    del group["attributes"]["transactions"][0][field]

    with pytest.raises(ValueError):
        parse_firefly_historical_record(group)