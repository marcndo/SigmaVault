from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.evidence import FinancialEvidence


def require_actual_transaction(
    transaction: FinancialTransaction,
) -> None:
    """Require a transaction to be classified as actual."""

    if transaction.status != "actual":
        raise ValueError("Transaction is not an actual")
    
    
def require_settled_evidence(
    evidence: FinancialEvidence,
) -> None:
    """Require evidence to report a completed settlement."""

    if evidence.settlement_status != "settled":
        raise ValueError("Evidence is not settled")


def validate_evidence_match(
    transaction: FinancialTransaction,
    evidence: FinancialEvidence,
) -> None:
    """Validate consistency between transaction and evidence."""

    if transaction.transaction_id != evidence.transaction_id:
        raise ValueError("Evidence transaction ID mismatch")

    if transaction.amount != evidence.amount:
        raise ValueError("Evidence amount mismatch")

    if transaction.currency != evidence.currency:
        raise ValueError("Evidence currency mismatch")

    if transaction.direction != evidence.direction:
        raise ValueError("Evidence direction mismatch")
    
def validate_settlement_candidate(
    transaction: FinancialTransaction,
    evidence: FinancialEvidence,
) -> None:
    """Validate a candidate against current eligibility rules."""

    require_actual_transaction(transaction)
    validate_evidence_match(transaction, evidence)
    require_settled_evidence(evidence)