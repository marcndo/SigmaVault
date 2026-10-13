import pytest

from decimal import Decimal

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.provenance import validate_transaction_provenance


def test_rejects_provenance_for_different_transaction():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="forecast",
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
        validate_transaction_provenance(
            transaction,
            provenance,
        )
        
        
def test_accepts_provenance_for_matching_transaction():
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
        verified=False,
    )

    result = validate_transaction_provenance(
        transaction,
        provenance,
    )

    assert result is None