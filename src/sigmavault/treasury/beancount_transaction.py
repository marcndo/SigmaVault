from datetime import date
from decimal import Decimal
import re
from beancount.parser.parser import parse_string
from beancount.core.data import Transaction

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import (
    TransactionProvenance,
    require_verified_actual,
)
from sigmavault.treasury.beancount_decision_journal import (
    escape_beancount_string,
)


ACCOUNT_PATTERN = re.compile(
    r"^(Assets|Liabilities|Equity|Income|Expenses)"
    r"(?::[A-Z][A-Za-z0-9-]*)+$"
)


def render_financial_transaction(
    *,
    transaction: FinancialTransaction,
    provenance: TransactionProvenance,
    transaction_date: date,
    payee: str,
    narration: str,
    asset_account: str,
    counterparty_account: str,
) -> str:
    """Render one verified XAF transaction as balanced Beancount."""

    require_verified_actual(transaction, provenance)

    if type(transaction_date) is not date:
        raise TypeError("transaction_date must be a date")

    if transaction.amount <= Decimal("0"):
        raise ValueError("Transaction amount must be positive")

    if transaction.currency != "XAF":
        raise ValueError("Only XAF transactions are supported")

    if not isinstance(payee, str) or not payee.strip():
        raise ValueError("Payee must not be blank")

    if not isinstance(narration, str) or not narration.strip():
        raise ValueError("Narration must not be blank")

    for account in (asset_account, counterparty_account):
        if not isinstance(account, str) or not ACCOUNT_PATTERN.fullmatch(account):
            raise ValueError(f"Invalid Beancount account: {account}")

    if asset_account == counterparty_account:
        raise ValueError("Posting accounts must be different")

    if not asset_account.startswith("Assets:"):
        raise ValueError("asset_account must be an Assets account")

    if transaction.direction == "expense":
        if not counterparty_account.startswith("Expenses:"):
            raise ValueError("Expense requires an Expenses account")

        asset_amount = -transaction.amount
        counterparty_amount = transaction.amount

    elif transaction.direction == "income":
        if not counterparty_account.startswith("Income:"):
            raise ValueError("Income requires an Income account")

        asset_amount = transaction.amount
        counterparty_amount = -transaction.amount

    else:
        raise ValueError("Unsupported transaction direction")

    def amount_text(value: Decimal) -> str:
        return format(value, "f")

    entry = (
        f'{transaction_date.isoformat()} * '
        f'"{escape_beancount_string(payee)}" '
        f'"{escape_beancount_string(narration)}"\n'
        f'  source_id: "{escape_beancount_string(transaction.transaction_id)}"\n'
        f'  source_provider: "{escape_beancount_string(provenance.source)}"\n'
        f'  {asset_account}  {amount_text(asset_amount)} XAF\n'
        f'  {counterparty_account}  {amount_text(counterparty_amount)} XAF\n'
    )
    entries, errors, _ = parse_string(entry)

    if errors or len(entries) != 1:
        raise ValueError(
            "Generated Beancount transaction is invalid: "
            f"{errors!r}"
        )

    if not isinstance(entries[0], Transaction):
        raise ValueError("Generated directive is not a transaction")

        if not isinstance(entries[0], Transaction):
            raise ValueError("Generated directive is not a transaction")

    return entry