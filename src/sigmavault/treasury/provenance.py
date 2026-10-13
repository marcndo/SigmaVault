from dataclasses import dataclass
from sigmavault.treasury.domain import FinancialTransaction

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionProvenance:
    transaction_id: str
    source: str
    verified: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.transaction_id, str)
            or not self.transaction_id.strip()
        ):
            raise ValueError("Invalid transaction ID")
        if (
        not isinstance(self.source, str)
        or not self.source.strip()
        ):
            raise ValueError("Invalid provenance source")
        if type(self.verified) is not bool:
            raise ValueError("Invalid verification status")
        

def validate_transaction_provenance(
    transaction: FinancialTransaction,
    provenance: TransactionProvenance,
) -> None:
    """Validate that provenance belongs to the given transaction."""
    if transaction.transaction_id != provenance.transaction_id:
        raise ValueError("Transaction ID mismatch")
    
    
def require_verified_actual(
    transaction: FinancialTransaction,
    provenance: TransactionProvenance,
) -> None:
    """Reject transactions that are not classified as actuals."""
    if transaction.status != "actual":
        raise ValueError("Transaction is not an actual")
    if not provenance.verified:
        raise ValueError("Transaction is not verified")
    
    validate_transaction_provenance(transaction, provenance)