from datetime import date
from decimal import Decimal

import pytest

from beancount.core.data import Transaction
from beancount.parser.parser import parse_string

from sigmavault.treasury.domain import FinancialTransaction
from sigmavault.treasury.provenance import TransactionProvenance
from sigmavault.treasury.beancount_transaction import (
    render_financial_transaction,
)


def make_transaction(
    direction="expense",
    status="actual",
    amount="25000",
):
    return FinancialTransaction(
        transaction_id="BANK-001",
        amount=Decimal(amount),
        currency="XAF",
        status=status,
        direction=direction,
    )


def make_provenance(verified=True):
    return TransactionProvenance(
        transaction_id="BANK-001",
        source="bank_statement",
        verified=verified,
    )


def render(transaction, provenance, counterparty_account):
    return render_financial_transaction(
        transaction=transaction,
        provenance=provenance,
        transaction_date=date(2026, 10, 17),
        payee="Internet Provider",
        narration="Monthly internet payment",
        asset_account="Assets:Bank:Operating",
        counterparty_account=counterparty_account,
    )


def test_verified_expense_creates_balanced_transaction():
    entry = render(
        make_transaction(),
        make_provenance(),
        "Expenses:Internet",
    )

    entries, errors, _ = parse_string(entry)

    assert errors == []
    assert len(entries) == 1
    assert isinstance(entries[0], Transaction)

    postings = entries[0].postings

    assert sum(
        posting.units.number for posting in postings
    ) == Decimal("0")

    assert postings[0].units.number == Decimal("-25000")
    assert postings[1].units.number == Decimal("25000")


def test_verified_income_creates_balanced_transaction():
    entry = render(
        make_transaction(direction="income"),
        make_provenance(),
        "Income:Sales",
    )

    entries, errors, _ = parse_string(entry)

    assert errors == []
    assert postings_balance(entries[0])


def postings_balance(transaction):
    return sum(
        posting.units.number for posting in transaction.postings
    ) == Decimal("0")


def test_unverified_transaction_is_rejected():
    with pytest.raises(ValueError, match="not verified"):
        render(
            make_transaction(),
            make_provenance(verified=False),
            "Expenses:Internet",
        )


def test_forecast_is_rejected():
    with pytest.raises(ValueError, match="not an actual"):
        render(
            make_transaction(status="forecast"),
            make_provenance(),
            "Expenses:Internet",
        )


def test_zero_amount_is_rejected():
    with pytest.raises(ValueError, match="positive"):
        render(
            make_transaction(amount="0"),
            make_provenance(),
            "Expenses:Internet",
        )


def test_expense_cannot_use_income_account():
    with pytest.raises(ValueError, match="Expenses account"):
        render(
            make_transaction(),
            make_provenance(),
            "Income:Sales",
        )


def test_provenance_must_match_transaction():
    provenance = TransactionProvenance(
        transaction_id="DIFFERENT-ID",
        source="bank_statement",
        verified=True,
    )

    with pytest.raises(ValueError, match="ID mismatch"):
        render(
            make_transaction(),
            provenance,
            "Expenses:Internet",
        )