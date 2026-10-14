import pytest
from dataclasses import FrozenInstanceError
from sigmavault.treasury.provider_identity import (
    ProviderTransactionIdentity,
)


def test_provider_transaction_identity_stores_fields():
    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    assert identity.provider_id == "bank_a"
    assert identity.transaction_reference == "TXN-001"
    
    
@pytest.mark.parametrize(
    "provider_id",
    ["", " ", "\t", "\n"],
)
def test_provider_identity_rejects_blank_provider_id(provider_id):
    with pytest.raises(
        ValueError,
        match="Provider ID must not be blank",
    ):
        ProviderTransactionIdentity(
            provider_id=provider_id,
            transaction_reference="TXN-001",
        )
        
        
@pytest.mark.parametrize(
    "provider_id",
    [
        None,
        12345,
        True,
        12.5,
        [],
        {},
    ],
)
def test_provider_identity_rejects_non_string_provider_id(provider_id):
    with pytest.raises(
        ValueError,
        match="Provider ID must not be blank",
    ):
        ProviderTransactionIdentity(
            provider_id=provider_id,
            transaction_reference="TXN-001",
        )
        

@pytest.mark.parametrize(
    "transaction_reference",
    ["", " ", "\t", "\n"],
)
def test_provider_identity_rejects_blank_transaction_reference(
    transaction_reference,
):
    with pytest.raises(
        ValueError,
        match="Provider reference must not be blank",
    ):
        ProviderTransactionIdentity(
            provider_id="bank_a",
            transaction_reference=transaction_reference,
        )
        
@pytest.mark.parametrize(
    "transaction_reference",
    [
        None,
        12345,
        True,
        12.5,
        [],
        {},
    ],
)
def test_provider_identity_rejects_non_string_transaction_reference(
    transaction_reference,
):
    with pytest.raises(
        ValueError,
        match="Provider reference must not be blank",
    ):
        ProviderTransactionIdentity(
            provider_id="bank_a",
            transaction_reference=transaction_reference,
        )
        
        
def test_provider_identities_with_same_fields_are_equal():
    first = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    second = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    assert first == second
    assert first is not second
    
    
def test_provider_identities_with_different_providers_are_not_equal():
    first = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    second = ProviderTransactionIdentity(
        provider_id="bank_b",
        transaction_reference="TXN-001",
    )

    assert first != second
    

def test_provider_identities_with_different_references_are_not_equal():
    first = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    second = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-002",
    )

    assert first != second
    

@pytest.mark.parametrize(
    "field,new_value",
    [
        ("provider_id", "bank_b"),
        ("transaction_reference", "TXN-002"),
    ],
)
def test_provider_transaction_identity_is_immutable(field, new_value):
    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    with pytest.raises(FrozenInstanceError):
        setattr(identity, field, new_value)
        
        
def test_provider_transaction_identity_supports_set_membership():
    first = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    duplicate = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    different = ProviderTransactionIdentity(
        provider_id="bank_b",
        transaction_reference="TXN-001",
    )

    processed = {first}

    assert hash(first) == hash(duplicate)
    assert duplicate in processed
    assert different not in processed