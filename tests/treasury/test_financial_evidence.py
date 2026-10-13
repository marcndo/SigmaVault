from decimal import Decimal

from sigmavault.treasury.evidence import FinancialEvidence


def test_create_financial_evidence():
    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    assert evidence.evidence_id == "BANK-001"
    assert evidence.source == "bank_statement"
    assert evidence.transaction_id == "101"
    assert evidence.amount == Decimal("50000")
    assert evidence.currency == "XAF"
    assert evidence.direction == "income"
    assert evidence.settlement_status == "settled"
    
    
import pytest


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
def test_financial_evidence_rejects_invalid_id(invalid_id):
    with pytest.raises(
        ValueError,
        match="Invalid evidence ID",
    ):
        FinancialEvidence(
            evidence_id=invalid_id,
            source="bank_statement",
            transaction_id="101",
            amount=Decimal("50000"),
            currency="XAF",
            direction="income",
            settlement_status="settled",
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
def test_financial_evidence_rejects_invalid_source(
    invalid_source,
):
    with pytest.raises(
        ValueError,
        match="Invalid evidence source",
    ):
        FinancialEvidence(
            evidence_id="BANK-001",
            source=invalid_source,
            transaction_id="101",
            amount=Decimal("50000"),
            currency="XAF",
            direction="income",
            settlement_status="settled",
        )
        
        
@pytest.mark.parametrize(
    "invalid_transaction_id",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
    ],
)
def test_financial_evidence_rejects_invalid_transaction_id(
    invalid_transaction_id,
):
    with pytest.raises(
        ValueError,
        match="Invalid evidence transaction ID",
    ):
        FinancialEvidence(
            evidence_id="BANK-001",
            source="bank_statement",
            transaction_id=invalid_transaction_id,
            amount=Decimal("50000"),
            currency="XAF",
            direction="income",
            settlement_status="settled",
        )
        
        
@pytest.mark.parametrize(
    "invalid_amount",
    [
        Decimal("-1"),
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        None,
        100,
        100.5,
        "50000",
        [],
        {},
    ],
)
def test_financial_evidence_rejects_invalid_amount(
    invalid_amount,
):
    with pytest.raises(
        ValueError,
        match="Invalid evidence amount",
    ):
        FinancialEvidence(
            evidence_id="BANK-001",
            source="bank_statement",
            transaction_id="101",
            amount=invalid_amount,
            currency="XAF",
            direction="income",
            settlement_status="settled",
        )
        
        
@pytest.mark.parametrize(
    "valid_amount",
    [
        Decimal("0"),
        Decimal("1"),
        Decimal("50000"),
        Decimal("50000.50"),
        Decimal("999999999.99"),
    ],
)
def test_financial_evidence_accepts_valid_amount(
    valid_amount,
):
    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=valid_amount,
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    assert evidence.amount == valid_amount
    assert isinstance(evidence.amount, Decimal)
    
@pytest.mark.parametrize(
    "invalid_currency",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
        "USD",
        "EUR",
        "xaf",
        "XAF ",
    ],
)
def test_financial_evidence_rejects_invalid_currency(
    invalid_currency,
):
    with pytest.raises(
        ValueError,
        match="Invalid evidence currency",
    ):
        FinancialEvidence(
            evidence_id="BANK-001",
            source="bank_statement",
            transaction_id="101",
            amount=Decimal("50000"),
            currency=invalid_currency,
            direction="income",
            settlement_status="settled",
        )
        
        
@pytest.mark.parametrize(
    "invalid_direction",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
        "transfer",
        "deposit",
        "withdrawal",
        "INCOME",
        "Expense",
    ],
)
def test_financial_evidence_rejects_invalid_direction(
    invalid_direction,
):
    with pytest.raises(
        ValueError,
        match="Invalid evidence direction",
    ):
        FinancialEvidence(
            evidence_id="BANK-001",
            source="bank_statement",
            transaction_id="101",
            amount=Decimal("50000"),
            currency="XAF",
            direction=invalid_direction,
            settlement_status="settled",
        )
        
        
@pytest.mark.parametrize(
    "valid_direction",
    [
        "income",
        "expense",
    ],
)
def test_financial_evidence_accepts_valid_direction(
    valid_direction,
):
    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction=valid_direction,
        settlement_status="settled",
    )

    assert evidence.direction == valid_direction
    
    
@pytest.mark.parametrize(
    "invalid_settlement_status",
    [
        "",
        "   ",
        None,
        123,
        [],
        {},
        "completed",
        "success",
        "processing",
        "SETTLED",
        "Pending",
        "settled ",
    ],
)
def test_financial_evidence_rejects_invalid_settlement_status(
    invalid_settlement_status,
):
    with pytest.raises(
        ValueError,
        match="Invalid evidence settlement status",
    ):
        FinancialEvidence(
            evidence_id="BANK-001",
            source="bank_statement",
            transaction_id="101",
            amount=Decimal("50000"),
            currency="XAF",
            direction="income",
            settlement_status=invalid_settlement_status,
        )
        
        
@pytest.mark.parametrize(
    "valid_settlement_status",
    [
        "pending",
        "settled",
        "failed",
    ],
)
def test_financial_evidence_accepts_valid_settlement_status(
    valid_settlement_status,
):
    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status=valid_settlement_status,
    )

    assert evidence.settlement_status == valid_settlement_status