from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.integrations.firefly.historical_record import (
    FireflyHistoricalRecord,
)

@dataclass(frozen=True)
class ParsedFireflyTransaction:
    transaction_id: str
    amount: Decimal
    currency: str
    direction: str

def parse_firefly_transaction(
    group: dict,
) -> FinancialTransaction:
    """Convert a single-split Firefly group into a treasury transaction."""

    if not isinstance(group, dict):
        raise ValueError("Invalid Firefly transaction group structure")
    
    group_id = group.get("id")
    
    if not isinstance(group_id, str) or not group_id.strip():
        raise ValueError("Invalid Firefly transaction group ID")
    
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
    
    if (
        not isinstance(transaction_type, str)
        or transaction_type not in direction_map
    ):
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
    currency = transaction["currency_code"]

def parse_firefly_split(group: dict) -> ParsedFireflyTransaction:
    """Validate and normalize a single-split Firefly transaction group."""

    if not isinstance(group, dict):
        raise ValueError("Invalid Firefly transaction group structure")

    group_id = group.get("id")

    if not isinstance(group_id, str) or not group_id.strip():
        raise ValueError("Invalid Firefly transaction group ID")

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
        raise ValueError("Invalid Firefly transaction split structure")

    required_fields = {"type", "amount", "currency_code"}

    if not required_fields.issubset(transaction):
        raise ValueError("Invalid Firefly transaction split structure")

    direction_map = {
        "withdrawal": "expense",
        "deposit": "income",
    }

    transaction_type = transaction["type"]

    if (
        not isinstance(transaction_type, str)
        or transaction_type not in direction_map
    ):
        raise ValueError("Unsupported Firefly transaction type")

    raw_amount = transaction["amount"]

    if not isinstance(raw_amount, str):
        raise ValueError("Invalid Firefly transaction amount")

    try:
        amount = Decimal(raw_amount)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Invalid Firefly transaction amount") from exc

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Invalid Firefly transaction amount")

    currency = transaction["currency_code"]

    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("Invalid Firefly transaction currency")

    return ParsedFireflyTransaction(
        transaction_id=group_id,
        amount=amount,
        currency=currency,
        direction=direction_map[transaction_type],
    )


def parse_firefly_transaction(
    group: dict,
    status: str,
) -> FinancialTransaction:
    """Preserve the existing treasury-domain parsing contract."""

    parsed = parse_firefly_split(group)

    return FinancialTransaction(
        transaction_id=parsed.transaction_id,
        amount=parsed.amount,
        currency=parsed.currency,
        status=status,
        direction=parsed.direction,
    )

def parse_firefly_transaction(
    group: dict,
    status: str,
) -> FinancialTransaction:
    """Preserve the existing treasury-domain parsing contract."""

    parsed = parse_firefly_split(group)

    return FinancialTransaction(
        transaction_id=parsed.transaction_id,
        amount=parsed.amount,
        currency=parsed.currency,
        status=status,
        direction=parsed.direction,
    )

def parse_firefly_historical_record(
    group: dict,
) -> FireflyHistoricalRecord:
    """Normalize a dated, categorized Firefly transaction for forecasting."""

    transaction = parse_firefly_transaction(
        group,
        status="forecast",
    )

    split = group["attributes"]["transactions"][0]

    category = split.get("category_name")
    subcategory = split.get("description")
    raw_date = split.get("date")

    if not isinstance(category, str) or not category.strip():
        raise ValueError("Missing Firefly transaction category")

    if not isinstance(subcategory, str) or not subcategory.strip():
        raise ValueError("Missing Firefly transaction description")

    if not isinstance(raw_date, str):
        raise ValueError("Missing Firefly transaction date")

    try:
        transaction_date = date.fromisoformat(raw_date[:10])
    except ValueError as exc:
        raise ValueError("Invalid Firefly transaction date") from exc

    return FireflyHistoricalRecord(
        record_id=transaction.transaction_id,
        category=category,
        subcategory=subcategory,
        record_type=transaction.direction,
        status="unverified",
        due_date=transaction_date,
        amount=transaction.amount,
        currency=transaction.currency,
    )