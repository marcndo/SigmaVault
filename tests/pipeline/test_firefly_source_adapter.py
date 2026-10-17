from decimal import Decimal

import pytest

from sigmavault.pipeline.coordinator import FinancialDataPipeline
from sigmavault.pipeline.firefly_adapter import FireflySourceAdapter


class FakeFireflyClient:
    def __init__(self, groups):
        self.groups = groups
        self.requested_account = None

    def get_account_transactions(self, account_id):
        self.requested_account = account_id
        return self.groups


def make_group(
    group_id="101",
    amount="25000",
    transaction_type="withdrawal",
):
    return {
        "id": group_id,
        "attributes": {
            "transactions": [
                {
                    "type": transaction_type,
                    "amount": amount,
                    "currency_code": "XAF",
                    "description": "Office supplies",
                    "category_name": "Operations",
                    "date": "2026-10-01",
                }
            ]
        },
    }


def test_firefly_adapter_uses_unified_pipeline():
    client = FakeFireflyClient([make_group()])

    adapter = FireflySourceAdapter(
        client=client,
        account_id=17,
        namespace="test-firefly/account-17",
    )

    result = FinancialDataPipeline().process(adapter)

    assert client.requested_account == 17
    assert result.source_count == 1
    assert result.duplicate_count == 0

    record = result.records[0]

    assert record.identity.provider == "firefly"
    assert record.identity.record_id == "101"
    assert record.amount == Decimal("25000")
    assert record.direction == "expense"
    assert record.status == "unverified"
    assert record.source == "confirmed"
    assert record.transaction_date.isoformat() == "2026-10-01"
    assert record.due_date is None


def test_firefly_deposit_maps_to_income():
    client = FakeFireflyClient([
        make_group(transaction_type="deposit")
    ])

    adapter = FireflySourceAdapter(
        client=client,
        account_id=17,
        namespace="test-firefly/account-17",
    )

    record = adapter.fetch_records()[0]

    assert record.direction == "income"


def test_firefly_adapter_rejects_missing_date():
    group = make_group()
    del group["attributes"]["transactions"][0]["date"]

    adapter = FireflySourceAdapter(
        client=FakeFireflyClient([group]),
        account_id=17,
        namespace="test-firefly/account-17",
    )

    with pytest.raises(ValueError, match="Missing Firefly transaction date"):
        adapter.fetch_records()


def test_firefly_adapter_rejects_invalid_account_id():
    with pytest.raises(ValueError, match="account_id"):
        FireflySourceAdapter(
            client=FakeFireflyClient([]),
            account_id=0,
            namespace="test-firefly/account-17",
        )


def test_firefly_adapter_propagates_invalid_amount():
    adapter = FireflySourceAdapter(
        client=FakeFireflyClient([make_group(amount="invalid")]),
        account_id=17,
        namespace="test-firefly/account-17",
    )

    with pytest.raises(ValueError, match="Invalid Firefly transaction amount"):
        adapter.fetch_records()