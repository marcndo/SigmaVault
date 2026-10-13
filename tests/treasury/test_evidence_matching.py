import pytest
from decimal import Decimal

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.evidence import FinancialEvidence
from sigmavault.treasury.evidence_matching import (
    require_actual_transaction,
    require_settled_evidence,
    validate_evidence_match,
    validate_settlement_candidate,
)


def test_evidence_matching_rejects_transaction_id_mismatch():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="999",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    with pytest.raises(
        ValueError,
        match="Evidence transaction ID mismatch",
    ):
        validate_evidence_match(transaction, evidence)
        
        
def test_evidence_matching_accepts_matching_transaction_ids():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    result = validate_evidence_match(transaction, evidence)

    assert result is None
    
    
    
def test_evidence_matching_rejects_amount_mismatch():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("45000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    with pytest.raises(
        ValueError,
        match="Evidence amount mismatch",
    ):
        validate_evidence_match(transaction, evidence)
        
        
def test_evidence_matching_accepts_equal_amounts():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000.00"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    result = validate_evidence_match(transaction, evidence)

    assert result is None
    
    
def test_evidence_matching_rejects_direction_mismatch():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="expense",
        settlement_status="settled",
    )

    with pytest.raises(
        ValueError,
        match="Evidence direction mismatch",
    ):
        validate_evidence_match(transaction, evidence)
        
        
@pytest.mark.parametrize(
    "direction",
    [
        "income",
        "expense",
    ],
)
def test_evidence_matching_accepts_matching_directions(
    direction,
):
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction=direction,
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction=direction,
        settlement_status="settled",
    )

    result = validate_evidence_match(transaction, evidence)

    assert result is None
    
    
@pytest.mark.parametrize(
    "settlement_status",
    [
        "pending",
        "failed",
    ],
)
def test_evidence_matching_accepts_matching_unsettled_evidence(
    settlement_status,
):
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status=settlement_status,
    )

    assert validate_evidence_match(transaction, evidence) is None
        
     
        
@pytest.mark.parametrize(
    "settlement_status",
    [
        "pending",
        "failed",
    ],
)
def test_require_settled_evidence_rejects_unsettled_status(
    settlement_status,
):
    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status=settlement_status,
    )

    with pytest.raises(
        ValueError,
        match="Evidence is not settled",
    ):
        require_settled_evidence(evidence)
        
        
def test_require_settled_evidence_accepts_settled_status():
    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    result = require_settled_evidence(evidence)

    assert result is None
    
    
    
def test_evidence_matching_accepts_matching_forecast_transaction():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="forecast",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )
    assert validate_evidence_match(transaction, evidence) is None
        
        
        
def test_evidence_matching_accepts_actual_with_settled_evidence():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    result = validate_evidence_match(transaction, evidence)

    assert result is None
    
    
def test_require_actual_transaction_rejects_forecast():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="forecast",
        direction="income",
    )

    with pytest.raises(
        ValueError,
        match="Transaction is not an actual",
    ):
        require_actual_transaction(transaction)
        
        
def test_require_actual_transaction_accepts_actual():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    result = require_actual_transaction(transaction)

    assert result is None
    
def test_settlement_candidate_accepts_matching_actual_and_settled_evidence():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    result = validate_settlement_candidate(transaction, evidence)

    assert result is None
    
    
def test_settlement_candidate_rejects_forecast_transaction():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="forecast",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="settled",
    )

    with pytest.raises(
        ValueError,
        match="Transaction is not an actual",
    ):
        validate_settlement_candidate(transaction, evidence)
        
        
@pytest.mark.parametrize(
    "settlement_status",
    ["pending", "failed"],
)
def test_settlement_candidate_rejects_unsettled_evidence(
    settlement_status,
):
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status=settlement_status,
    )

    with pytest.raises(
        ValueError,
        match="Evidence is not settled",
    ):
        validate_settlement_candidate(transaction, evidence)
        
@pytest.mark.parametrize(
    ("evidence_transaction_id", "evidence_amount", "evidence_direction", "error"),
    [
        ("999", Decimal("50000"), "income", "Evidence transaction ID mismatch"),
        ("101", Decimal("60000"), "income", "Evidence amount mismatch"),
        ("101", Decimal("50000"), "expense", "Evidence direction mismatch"),
    ],
)
def test_settlement_candidate_rejects_mismatched_evidence(
    evidence_transaction_id,
    evidence_amount,
    evidence_direction,
    error,
):
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="actual",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id=evidence_transaction_id,
        amount=evidence_amount,
        currency="XAF",
        direction=evidence_direction,
        settlement_status="settled",
    )

    with pytest.raises(ValueError, match=error):
        validate_settlement_candidate(transaction, evidence)
        
        
def test_matching_and_settlement_eligibility_are_separate():
    transaction = FinancialTransaction(
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        status="forecast",
        direction="income",
    )

    evidence = FinancialEvidence(
        evidence_id="BANK-001",
        source="bank_statement",
        transaction_id="101",
        amount=Decimal("50000"),
        currency="XAF",
        direction="income",
        settlement_status="pending",
    )

    # These records describe the same financial movement.
    assert validate_evidence_match(transaction, evidence) is None

    # But the forecast is not an eligible settlement candidate.
    with pytest.raises(
        ValueError,
        match="Transaction is not an actual",
    ):
     validate_settlement_candidate(transaction, evidence)