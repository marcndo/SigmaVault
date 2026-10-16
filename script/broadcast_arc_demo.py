from decimal import Decimal
from uuid import UUID

from eth_account import Account
from eth_account._utils.legacy_transactions import Transaction
from web3 import Web3

from sigmavault.integrations.arc.gateway import ArcGateway
from sigmavault.integrations.arc.payment_repository import PaymentRepository
from sigmavault.integrations.arc.transaction_reconciliation import (
    reconcile_transaction,
)

PAYMENT_ID = UUID("334481bd-3765-4473-82f4-bea1bd27bbdd")
SENDER = "0x5AfD92B052FF5691DcC9D6Bdc937efAebb756113"
RECIPIENT = "0x7dcC7f5fAe967aE72c93b88D287616b138d3abfF"
AMOUNT = Decimal("0.1")
CHAIN_ID = 5042002

repository = PaymentRepository("data/arc_demo_payments.sqlite3")
payment = repository.get(PAYMENT_ID)
prepared = repository.get_prepared_transaction(PAYMENT_ID)

assert payment is not None, "Payment authorization missing"
assert prepared is not None, "Prepared transaction missing"
assert payment.status.value == "broadcasting"

stored_hash, raw_hex = prepared
raw = Web3.to_bytes(hexstr=raw_hex)
tx = Transaction.from_bytes(raw)

assert Web3.to_hex(Web3.keccak(raw)).lower() == stored_hash.lower()
assert Account.recover_transaction(raw_hex).lower() == SENDER.lower()

recipient = Web3.to_checksum_address("0x" + tx.to.hex())
assert recipient.lower() == RECIPIENT.lower()

assert payment.sender.lower() == SENDER.lower()
assert payment.recipient.lower() == RECIPIENT.lower()
assert payment.amount == AMOUNT
assert payment.chain_id == CHAIN_ID

assert Decimal(tx.value) / Decimal(10**18) == AMOUNT
assert (tx.v - 35) // 2 == CHAIN_ID
assert tx.nonce == 0
assert tx.gas == 21000

gateway = ArcGateway("https://rpc.testnet.arc.io")
gateway.verify_network()

result = reconcile_transaction(
    gateway=gateway,
    payment=payment,
    transaction_hash=stored_hash,
    raw_transaction=raw_hex,
)

print("Current on-chain status:", result.status)

if result.status != "not_found":
    print("Transaction already visible or resolved. No broadcast.")
    raise SystemExit(0)

latest_nonce = gateway.web3.eth.get_transaction_count(
    SENDER, "latest"
)
pending_nonce = gateway.web3.eth.get_transaction_count(
    SENDER, "pending"
)

balance = gateway.web3.eth.get_balance(SENDER)
required = tx.value + tx.gas * tx.gasPrice

assert latest_nonce == pending_nonce == tx.nonce
assert balance >= required, "Insufficient balance"

print("\nARC TESTNET TRANSFER")
print("Payment ID:", PAYMENT_ID)
print("From:", SENDER)
print("To:", RECIPIENT)
print("Amount:", AMOUNT, "testnet USDC")
print("Transaction hash:", stored_hash)
print(
    "Maximum gas cost:",
    Decimal(tx.gas * tx.gasPrice) / Decimal(10**18),
    "USDC",
)

confirmation = input(
    "\nType BROADCAST 0.1 USDC to authorize submission: "
)

if confirmation != "BROADCAST 0.1 USDC":
    print("Cancelled. No broadcast performed.")
    raise SystemExit(0)

# Final checks immediately before submission.
result = reconcile_transaction(
    gateway=gateway,
    payment=payment,
    transaction_hash=stored_hash,
    raw_transaction=raw_hex,
)

if result.status != "not_found":
    print("Transaction state changed:", result.status)
    print("No broadcast performed.")
    raise SystemExit(0)

assert gateway.web3.eth.get_transaction_count(
    SENDER, "latest"
) == tx.nonce

assert gateway.web3.eth.get_transaction_count(
    SENDER, "pending"
) == tx.nonce

assert gateway.web3.eth.get_balance(SENDER) >= required

# Submit the exact previously signed transaction.
sent_hash = gateway.web3.eth.send_raw_transaction(raw)

assert Web3.to_hex(sent_hash).lower() == stored_hash.lower()

print("\nBroadcast accepted by RPC.")
print("Transaction hash:", Web3.to_hex(sent_hash))

result = reconcile_transaction(
    gateway=gateway,
    payment=payment,
    transaction_hash=stored_hash,
    raw_transaction=raw_hex,
)

print("Reconciled status:", result.status)
print("Block number:", result.block_number)
print("Database status:", repository.get(PAYMENT_ID).status.value)
print("Database confirmation is still pending.")
