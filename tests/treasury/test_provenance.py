import pytest

from sigmavault.treasury.provenance import (
    TransactionProvenance,
)


def test_transaction_provenance_accepts_verified_source():
    provenance = TransactionProvenance(
        transaction_id="101",
        source="bank_statement",
        verified=True,
    )

    assert provenance.transaction_id == "101"
    assert provenance.source == "bank_statement"
    assert provenance.verified is True
    
    
@pytest.mark.parametrize(
    "invalid_id",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
    ],
)
def test_transaction_provenance_rejects_invalid_id(
    invalid_id,
):
    with pytest.raises(
        ValueError,
        match="Invalid transaction ID",
    ):
        TransactionProvenance(
            transaction_id=invalid_id,
            source="bank_statement",
            verified=True,
        )
        
@pytest.mark.parametrize(
    "invalid_source",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
    ],
)
def test_transaction_provenance_rejects_invalid_source(
    invalid_source,
):
    with pytest.raises(
        ValueError,
        match="Invalid provenance source",
    ):
        TransactionProvenance(
            transaction_id="101",
            source=invalid_source,
            verified=True,
        )
        
@pytest.mark.parametrize(
    "invalid_verified",
    [
        None,
        1,
        0,
        "True",
        "False",
        "",
        [],
        {},
    ],
)
def test_transaction_provenance_rejects_invalid_verified(
    invalid_verified,
):
    with pytest.raises(
        ValueError,
        match="Invalid verification status",
    ):
        TransactionProvenance(
            transaction_id="101",
            source="bank_statement",
            verified=invalid_verified,
        )
    
        
@pytest.mark.parametrize(
    "verified",
    [True, False],
)
def test_transaction_provenance_accepts_valid_verification_status(
    verified,
):
    provenance = TransactionProvenance(
        transaction_id="101",
        source="bank_statement",
        verified=verified,
    )

    assert provenance.verified is verified