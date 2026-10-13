import pytest

from decimal import Decimal

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.provenance import require_verified_actual


def test_forecast_cannot_qualify_as_verified_actual():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="forecast",
        direction="income",
    )

    provenance = TransactionProvenance(
        transaction_id="101",
        source="bank_statement",
        verified=True,
    )

    with pytest.raises(
        ValueError,
        match="Transaction is not an actual",
    ):
        require_verified_actual(
            transaction,
            provenance,
        )
        
        
def test_unverified_actual_cannot_qualify_as_verified_actual():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    provenance = TransactionProvenance(
        transaction_id="101",
        source="bank_statement",
        verified=False,
    )

    with pytest.raises(
        ValueError,
        match="Transaction is not verified",
    ):
        require_verified_actual(
            transaction,
            provenance,
        )
 
        
def test_actual_with_mismatched_provenance_is_rejected():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    provenance = TransactionProvenance(
        transaction_id="999",
        source="bank_statement",
        verified=True,
    )

    with pytest.raises(
        ValueError,
        match="Transaction ID mismatch",
    ):
        require_verified_actual(
            transaction,
            provenance,
        )
        

def test_accepts_actual_with_matching_verified_provenance():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    provenance = TransactionProvenance(
        transaction_id="101",
        source="bank_statement",
        verified=True,
    )

    result = require_verified_actual(
        transaction,
        provenance,
    )

    assert result is None