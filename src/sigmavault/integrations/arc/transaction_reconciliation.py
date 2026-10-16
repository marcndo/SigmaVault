from dataclasses import dataclass
from decimal import Decimal

from eth_account import Account
from web3 import Web3
from web3.exceptions import TransactionNotFound

from sigmavault.integrations.arc.gateway import (
    ARC_TESTNET_CHAIN_ID,
    NATIVE_USDC_DECIMALS,
    ArcGateway,
)
from sigmavault.integrations.arc.payment_authorization import (
    PaymentAuthorization,
)


@dataclass(frozen=True)
class ReconciliationResult:
    transaction_hash: str
    status: str
    block_number: int | None


def reconcile_transaction(
    *,
    gateway: ArcGateway,
    payment: PaymentAuthorization,
    transaction_hash: str,
    raw_transaction: str,
) -> ReconciliationResult:
    """Check a prepared payment against Arc without broadcasting."""

    gateway.verify_network()

    raw_bytes = Web3.to_bytes(hexstr=raw_transaction)
    actual_hash = Web3.to_hex(Web3.keccak(raw_bytes))

    if actual_hash.lower() != transaction_hash.lower():
        raise ValueError("Stored transaction hash mismatch")

    sender = Account.recover_transaction(raw_transaction)

    if sender.lower() != payment.sender.lower():
        raise ValueError("Transaction sender mismatch")

    try:
        transaction = gateway.web3.eth.get_transaction(transaction_hash)
    except TransactionNotFound:
        return ReconciliationResult(
            transaction_hash=transaction_hash,
            status="not_found",
            block_number=None,
        )

    if transaction["from"].lower() != payment.sender.lower():
        raise ValueError("On-chain sender mismatch")

    if not transaction["to"] or (
        transaction["to"].lower() != payment.recipient.lower()
    ):
        raise ValueError("On-chain recipient mismatch")

    expected_value = payment.amount * Decimal(
        10**NATIVE_USDC_DECIMALS
    )

    if expected_value != expected_value.to_integral_value():
        raise ValueError("Invalid payment precision")

    if transaction["value"] != int(expected_value):
        raise ValueError("On-chain amount mismatch")

    chain_id = transaction.get("chainId")

    if chain_id != ARC_TESTNET_CHAIN_ID:
        raise ValueError("On-chain chain ID mismatch")

    try:
        receipt = gateway.web3.eth.get_transaction_receipt(
            transaction_hash
        )
    except TransactionNotFound:
        return ReconciliationResult(
            transaction_hash=transaction_hash,
            status="pending",
            block_number=None,
        )

    if receipt["status"] != 1:
        return ReconciliationResult(
            transaction_hash=transaction_hash,
            status="failed",
            block_number=receipt["blockNumber"],
        )

    return ReconciliationResult(
        transaction_hash=transaction_hash,
        status="confirmed",
        block_number=receipt["blockNumber"],
    )
