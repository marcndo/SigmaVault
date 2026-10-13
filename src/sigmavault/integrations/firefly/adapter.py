from decimal import Decimal, InvalidOperation

from sigmavault.treasury.domain import FinancialTransaction


def parse_firefly_transaction(
    group: dict,
    status: str,
) -> FinancialTransaction:
    """Convert a single-split Firefly group into a treasury transaction."""

    if not isinstance(group, dict):
        raise ValueError("Invalid Firefly transaction group structure")
    
    attributes = group.get("attributes")
    
    if not isinstance(attributes, dict):
        raise ValueError("Invalid Firefly transaction group structure")
    
    if "transactions" not in attributes:
        raise ValueError("Invalid Firefly transaction group structure")
    
    transactions = attributes["transactions"]    
    if not isinstance(transactions, list) or len(transactions) != 1:
        raise ValueError(
            "Firefly transaction group must contain exactly one split"
        )
    transaction = transactions[0]
    
    if not isinstance(transaction, dict):
        raise ValueError(
            "Invalid Firefly transaction split structure"
        )
    
    required_fields = {"type", "amount", "currency_code"}
    
    if not required_fields.issubset(transaction):
        raise ValueError(
            "Invalid Firefly transaction split structure"
        )
    
    transaction_type = transaction["type"]
    direction_map = {
        "withdrawal": "expense",
        "deposit": "income",
    }
    
    if transaction_type not in direction_map:
        raise ValueError("Unsupported Firefly transaction type")
    
    direction = direction_map[transaction_type]
        
    raw_amount = transaction["amount"]
    
    if not isinstance(raw_amount, str):
        raise ValueError("Invalid Firefly transaction amount")
    
    try:
        amount = Decimal(raw_amount)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(
            "Invalid Firefly transaction amount"
        ) from exc
    
    return FinancialTransaction(
        transaction_id=group["id"],
        amount=amount,
        currency=transaction["currency_code"],
        status=status,
        direction=direction,
    )