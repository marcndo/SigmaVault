import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from beancount.loader import load_string
from cryptography.hazmat.primitives import serialization

from sigmavault.integrations.arc.gateway import ArcGateway
from sigmavault.integrations.arc.payment_repository import PaymentRepository
from sigmavault.integrations.arc.transaction_reconciliation import (
    reconcile_transaction,
)
from sigmavault.treasury.signed_decision_audit import (
    hash_beancount_entry,
)

PAYMENT_ID = UUID("334481bd-3765-4473-82f4-bea1bd27bbdd")
EXPECTED_HASH = "0xf5a65912292a59d11f83a46a26a9aa89bd66e4f31dc03ecf6d83a1660d85ca9d"

OUTPUT = Path("data/arc_payment_evidence")
LEDGER = OUTPUT / f"{PAYMENT_ID}.beancount"
EVIDENCE = OUTPUT / f"{PAYMENT_ID}.json"


def main():
    repository = PaymentRepository("data/arc_demo_payments.sqlite3")
    payment = repository.get(PAYMENT_ID)
    prepared = repository.get_prepared_transaction(PAYMENT_ID)

    assert payment is not None
    assert prepared is not None
    assert payment.status.value == "confirmed"

    tx_hash, raw_transaction = prepared
    assert tx_hash.lower() == EXPECTED_HASH.lower()

    gateway = ArcGateway("https://rpc.testnet.arc.io")

    result = reconcile_transaction(
        gateway=gateway,
        payment=payment,
        transaction_hash=tx_hash,
        raw_transaction=raw_transaction,
    )

    assert result.status == "confirmed"
    assert result.block_number is not None

    transaction = gateway.web3.eth.get_transaction(tx_hash)
    receipt = gateway.web3.eth.get_transaction_receipt(tx_hash)
    block = gateway.web3.eth.get_block(result.block_number)

    assert receipt["status"] == 1
    assert transaction["blockNumber"] == result.block_number
    assert receipt["transactionHash"].hex().lower().removeprefix("0x") == tx_hash.lower().removeprefix("0x")

    amount = payment.amount
    assert amount == Decimal("0.1")

    event_date = datetime.fromtimestamp(
        block["timestamp"], timezone.utc
    ).date()

    # These are transfers between two testnet wallets, not business revenue.
    ledger = (
        f'{event_date} * "SigmaVault" "Confirmed Arc Testnet transfer"\n'
        f'  payment_id: "{PAYMENT_ID}"\n'
        f'  transaction_hash: "{tx_hash}"\n'
        f'  block_number: "{result.block_number}"\n'
        f'  chain_id: "5042002"\n'
        f'  Assets:ArcTestnet:Treasury  -{amount} USDC\n'
        f'  Assets:ArcTestnet:Recipient  {amount} USDC\n'
    )

    # Standalone parsing with Beancount requires account opening directives.
    validation_document = (
        '2000-01-01 open Assets:ArcTestnet:Treasury USDC\n'
        '2000-01-01 open Assets:ArcTestnet:Recipient USDC\n'
        + ledger
    )
    entries, errors, _ = load_string(validation_document)
    assert not errors, errors

    postings = entries[-1].postings
    assert sum((p.units.number for p in postings), Decimal("0")) == 0

    # Use the existing persistent Ed25519 audit signing key.
    key_path = Path("data/keys/audit_signing_key.pem")
    assert key_path.exists(), "Audit signing key file missing"

    private_key = serialization.load_pem_private_key(
        key_path.read_bytes(),
        password=None,
    )
    public_key = private_key.public_key()

    ledger_hash = hash_beancount_entry(ledger)

    evidence_payload = {
        "schema": "sigmavault-arc-payment-v1",
        "payment_id": str(PAYMENT_ID),
        "chain_id": 5042002,
        "transaction_hash": tx_hash,
        "block_number": result.block_number,
        "sender": payment.sender,
        "recipient": payment.recipient,
        "amount": str(amount),
        "currency": "USDC",
        "ledger_sha256": ledger_hash,
    }

    canonical = json.dumps(
        evidence_payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    signature = private_key.sign(canonical)
    public_key.verify(signature, canonical)

    document = {
        "payload": evidence_payload,
        "signature_hex": signature.hex(),
        "public_key_pem": public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8"),
    }

    ledger_bytes = ledger.encode("utf-8")
    evidence_bytes = (
        json.dumps(document, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    # Never silently replace existing accounting or signature evidence.
    for path, expected in (
        (LEDGER, ledger_bytes),
        (EVIDENCE, evidence_bytes),
    ):
        if path.exists() and path.read_bytes() != expected:
            raise RuntimeError(f"Existing evidence differs: {path}")

    for path, content in (
        (LEDGER, ledger_bytes),
        (EVIDENCE, evidence_bytes),
    ):
        if not path.exists():
            with path.open("xb") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())

    print("Arc transaction confirmed:", tx_hash)
    print("Block number:", result.block_number)
    print("Balanced Beancount ledger:", LEDGER)
    print("Ledger SHA-256:", ledger_hash)
    print("Ed25519 signature verified: True")
    print("Signed evidence:", EVIDENCE)
    print("Additional blockchain transfer: False")


if __name__ == "__main__":
    main()
