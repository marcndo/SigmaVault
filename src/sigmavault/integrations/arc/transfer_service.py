from dataclasses import dataclass
from decimal import Decimal
from eth_utils import keccak

from eth_account import Account
from web3 import Web3

from sigmavault.integrations.arc.gateway import (
    ARC_TESTNET_CHAIN_ID,
    NATIVE_USDC_DECIMALS,
    ArcGateway,
)


MAX_DEMO_TRANSFER = Decimal("1")


@dataclass(frozen=True)
class VerifiedTransfer:
    transaction_hash: str
    block_number: int
    sender: str
    recipient: str
    amount: Decimal
    status: str

@dataclass(frozen=True)
class PreparedTransfer:
    transaction_hash: str
    raw_transaction: str
    sender: str
    recipient: str
    amount: Decimal
    nonce: int


def prepare_demo_transfer(
    *,
    gateway: ArcGateway,
    private_key: str,
    approved_recipient: str,
    amount: Decimal,
) -> PreparedTransfer:
    """Sign a restricted Arc Testnet transfer without broadcasting."""

    gateway.verify_network()

    if not isinstance(amount, Decimal):
        raise TypeError("Amount must be Decimal")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Amount must be positive and finite")

    if amount > MAX_DEMO_TRANSFER:
        raise ValueError("Demo transfer exceeds 1 USDC")

    units = amount * Decimal(10**NATIVE_USDC_DECIMALS)

    if units != units.to_integral_value():
        raise ValueError("Amount exceeds native USDC precision")

    if not Web3.is_address(approved_recipient):
        raise ValueError("Invalid recipient")

    sender = Account.from_key(private_key)
    recipient = Web3.to_checksum_address(approved_recipient)

    if sender.address.lower() == recipient.lower():
        raise ValueError("Sender and recipient must differ")

    balance = gateway.get_native_balance(sender.address)
    gas_price = gateway.web3.eth.gas_price
    gas_limit = 21000
    value = int(units)

    required_balance = Decimal(
        value + gas_limit * gas_price
    ) / Decimal(10**NATIVE_USDC_DECIMALS)

    if balance < required_balance:
        raise ValueError("Insufficient balance including gas")

    nonce = gateway.web3.eth.get_transaction_count(
        sender.address, "pending"
    )

    transaction = {
        "chainId": ARC_TESTNET_CHAIN_ID,
        "nonce": nonce,
        "to": recipient,
        "value": value,
        "gas": gas_limit,
        "gasPrice": gas_price,
    }

    signed = sender.sign_transaction(transaction)
    raw_transaction = signed.raw_transaction

    return PreparedTransfer(
        transaction_hash=Web3.to_hex(keccak(raw_transaction)),
        raw_transaction=Web3.to_hex(raw_transaction),
        sender=sender.address,
        recipient=recipient,
        amount=amount,
        nonce=nonce,
    )

def execute_demo_transfer(
    *,
    gateway: ArcGateway,
    private_key: str,
    approved_recipient: str,
    amount: Decimal,
    human_approved: bool,
) -> VerifiedTransfer:
    """Execute a restricted Arc Testnet transfer.

    Only use with disposable testnet funds.
    """

    if not human_approved:
        raise PermissionError("Explicit human approval required")

    if not amount.is_finite() or amount <= 0:
        raise ValueError("Transfer amount must be positive")

    if amount > MAX_DEMO_TRANSFER:
        raise ValueError("Demo transfer exceeds 1 USDC limit")

    gateway.verify_network()

    if gateway.web3.eth.chain_id != ARC_TESTNET_CHAIN_ID:
        raise ValueError("Incorrect blockchain network")

    if not Web3.is_address(approved_recipient):
        raise ValueError("Invalid recipient")

    sender = Account.from_key(private_key)

    recipient = Web3.to_checksum_address(approved_recipient)

    if sender.address == recipient:
        raise ValueError("Cannot transfer to the same wallet")

    balance = gateway.get_native_balance(sender.address)

    if balance < amount:
        raise ValueError("Insufficient testnet balance")

    amount_wei = int(amount * Decimal(10**NATIVE_USDC_DECIMALS))

    nonce = gateway.web3.eth.get_transaction_count(
        sender.address,
        "pending",
    )

    transaction = {
        "chainId": ARC_TESTNET_CHAIN_ID,
        "from": sender.address,
        "to": recipient,
        "value": amount_wei,
        "nonce": nonce,
        "gas": 21000,
        "gasPrice": gateway.web3.eth.gas_price,
    }

    signed = sender.sign_transaction(transaction)

    tx_hash = gateway.web3.eth.send_raw_transaction(
        signed.raw_transaction
    )

    receipt = gateway.web3.eth.wait_for_transaction_receipt(
        tx_hash,
        timeout=90,
    )

    if receipt["status"] != 1:
        raise RuntimeError(
            f"Transaction failed: {tx_hash.to_0x_hex()}"
        )

    return VerifiedTransfer(
        transaction_hash=tx_hash.to_0x_hex(),
        block_number=receipt["blockNumber"],
        sender=sender.address,
        recipient=recipient,
        amount=amount,
        status="confirmed",
    )