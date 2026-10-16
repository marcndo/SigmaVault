import os
import sqlite3
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4
import hashlib
import json

from sigmavault.integrations.arc.wallet_snapshot import (
    capture_arc_wallet_snapshot,
)
from sigmavault.treasury.assessment import assess_forecast_liquidity
from sigmavault.treasury.agent_runner import run_treasury_agent
from sigmavault.treasury.forecasting import ExpenseForecast

from beancount.loader import load_string
from beancount.core.data import Transaction
from cryptography.hazmat.primitives import serialization
from uuid import UUID

from sigmavault.integrations.arc.payment_repository import PaymentRepository
from sigmavault.integrations.arc.transaction_reconciliation import (
    reconcile_transaction,
)
import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from pydantic_ai.models.test import TestModel

from sigmavault.integrations.arc.gateway import ArcGateway
from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.treasury.arc_forecast_workflow import (
    run_arc_forecast_workflow,
)
from sigmavault.treasury.decision_service import TreasuryDecisionService
from sigmavault.treasury.domain import Money
from sigmavault.treasury.signed_decision_audit import (
    verify_complete_decision_audit,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def main() -> None:
    rpc_url = os.getenv("ARC_RPC_URL", "https://rpc.testnet.arc.io")
    wallet_address = os.getenv(
        "ARC_WALLET_ADDRESS",
        "0x5AfD92B052FF5691DcC9D6Bdc937efAebb756113",
    )

    # Explicitly synthetic planning assumptions.
    assumed_cash = Money(Decimal("100000"), "XAF")
    assumed_buffer = Money(Decimal("20000"), "XAF")

    # Demo-only signing identity, generated for this run.
    # Do not confuse this with a persistent production signing key.
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # The local SQLite database contains financial decision metadata.
    # Keep it out of Git.
    database_path = Path("data/demo_treasury.sqlite3")
    database_path.parent.mkdir(parents=True, exist_ok=True)

    decision_id = f"DEMO-{uuid4().hex}"

    arc_gateway = ArcGateway(rpc_url)
    payment_evidence = verify_confirmed_demo_payment(arc_gateway)

    as_of = date.today().replace(day=1)

    # Explicitly synthetic expenses, not imported Firefly III records.
    forecasts = [
        ExpenseForecast(
            category="Office Bills",
            subcategory="Office rent",
            amount=Decimal("30000"),
            currency="XAF",
            due_date=as_of + timedelta(days=9),
            source="forecast",
            supporting_record_ids=(),
            explanation="Synthetic demonstration expense.",
        ),
        ExpenseForecast(
            category="Office Bills",
            subcategory="Internet",
            amount=Decimal("10000"),
            currency="XAF",
            due_date=as_of + timedelta(days=14),
            source="forecast",
            supporting_record_ids=(),
            explanation="Synthetic demonstration expense.",
        ),
    ]
    
    with sqlite3.connect(database_path) as connection:
        repository = SQLiteSignedDecisionRepository(connection)
    
        decision_service = TreasuryDecisionService(
            repository=repository,
            private_key=private_key,
            policy_version="demo-1.0.0",
        )
    
        position = assess_forecast_liquidity(
            forecasts=forecasts,
            available_cash=assumed_cash,
            minimum_buffer=assumed_buffer,
            planning_horizon=timedelta(days=30),
            as_of=as_of,
        )
    
        wallet_snapshot = capture_arc_wallet_snapshot(
            gateway=arc_gateway,
            address=wallet_address,
        )
    
        signed_decision = decision_service.assess_and_record(
            decision_id=decision_id,
            position=position,
            event_date=as_of,
        )
    
        recommendation = run_treasury_agent(
            position,
            evidence_verified=False,
            arc_wallet_snapshot=wallet_snapshot,
            model=TestModel(),
        )
    
        connection.commit()
    
        stored_record = repository.get_by_decision_id(decision_id)
    
        if stored_record is None:
            raise RuntimeError("Signed decision was not persisted")
    
        audit_verified = verify_complete_decision_audit(
            payload=stored_record.payload,
            journal_entry=stored_record.journal_entry,
            signature=stored_record.signature,
            public_key=public_key,
        )
    
        if not audit_verified:
            raise RuntimeError("Signed decision audit verification failed")
    
    print("\n=== SIGMAVAULT END-TO-END DEMO ===")

    print("\nSYNTHETIC FINANCIAL INPUTS / TREASURY")
    print("Cash source: SYNTHETIC PLANNING ASSUMPTION")
    print("Assumed cash:", assumed_cash.amount, "XAF")
    print(
        "Required liquidity:",
        position.required_liquidity.amount,
        "XAF",
    )
    print(
        "Deployable surplus:",
        position.deployable_surplus.amount,
        "XAF",
    )
    print("Liquidity status:", position.status.value)

    print("\nARC TESTNET")
    print("Chain ID:", wallet_snapshot.chain_id)
    print("Observed block:", wallet_snapshot.block_number)
    print(
        "Observed native USDC:",
        wallet_snapshot.native_usdc_balance,
    )

    print("\nAI RECOMMENDATION")
    print("Model: Pydantic AI TestModel (not a production LLM)")
    print("Action:", recommendation.action)
    print("Explanation:", recommendation.explanation)
    print("Human review:", recommendation.requires_human_review)

    print("\nSIGNED DECISION")
    print("Decision ID:", decision_id)
    print("Policy outcome:", stored_record.payload.outcome)
    print("SQLite record retrieved:", True)
    print("Signature and journal verified:", audit_verified)
    print("\nCONFIRMED ARC TESTNET PAYMENT")
    print("Payment ID:", payment_evidence["payment_id"])
    print("Amount:", payment_evidence["amount"], "USDC")
    print("Status:", payment_evidence["status"])
    print("Transaction hash:", payment_evidence["transaction_hash"])
    print("Block number:", payment_evidence["block_number"])
    print("Balanced Beancount ledger verified:", payment_evidence["ledger_verified"])
    print("Ed25519 payment evidence verified:", payment_evidence["signature_verified"])
    print("New payment executed during this demo:", False)

def verify_confirmed_demo_payment(arc_gateway: ArcGateway) -> dict:
    payment_id = UUID("334481bd-3765-4473-82f4-bea1bd27bbdd")

    repository = PaymentRepository("data/arc_demo_payments.sqlite3")
    payment = repository.get(payment_id)
    prepared = repository.get_prepared_transaction(payment_id)

    if payment is None or prepared is None:
        raise RuntimeError("Confirmed demo payment is missing")

    if payment.status.value != "confirmed":
        raise RuntimeError("Demo payment is not confirmed in SQLite")

    tx_hash, raw_transaction = prepared

    result = reconcile_transaction(
        gateway=arc_gateway,
        payment=payment,
        transaction_hash=tx_hash,
        raw_transaction=raw_transaction,
    )

    if result.status != "confirmed":
        raise RuntimeError(
            f"Demo payment is not confirmed on-chain: {result.status}"
        )

    evidence_dir = Path("data/arc_payment_evidence")

    ledger_bytes = (
        evidence_dir / f"{payment_id}.beancount"
    ).read_bytes()

    evidence = json.loads(
        (evidence_dir / f"{payment_id}.json").read_text()
    )

    payload = evidence["payload"]

    if payload["ledger_sha256"] != hashlib.sha256(
        ledger_bytes
    ).hexdigest():
        raise RuntimeError("Payment ledger hash mismatch")

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()

    public_key = serialization.load_pem_public_key(
        evidence["public_key_pem"].encode()
    )

    public_key.verify(
        bytes.fromhex(evidence["signature_hex"]),
        canonical,
    )

    assert payload["payment_id"] == str(payment_id)
    assert payload["transaction_hash"].lower() == tx_hash.lower()
    assert payload["block_number"] == result.block_number
    assert payload["chain_id"] == payment.chain_id
    assert payload["sender"].lower() == payment.sender.lower()
    assert payload["recipient"].lower() == payment.recipient.lower()
    assert Decimal(payload["amount"]) == payment.amount
    assert payload["currency"] == "USDC"

    validation_document = (
        "2000-01-01 open Assets:ArcTestnet:Treasury USDC\n"
        "2000-01-01 open Assets:ArcTestnet:Recipient USDC\n"
        + ledger_bytes.decode()
    )

    entries, errors, _ = load_string(validation_document)

    if errors:
        raise RuntimeError(f"Invalid payment ledger: {errors}")

    transactions = [
        entry for entry in entries
        if isinstance(entry, Transaction)
    ]

    if len(transactions) != 1:
        raise RuntimeError("Expected exactly one payment entry")

    entry = transactions[0]

    assert entry.meta["payment_id"] == str(payment_id)
    assert entry.meta["transaction_hash"].lower() == tx_hash.lower()

    postings = {
        posting.account: posting.units.number
        for posting in entry.postings
    }

    assert len(entry.postings) == 2
    assert postings["Assets:ArcTestnet:Treasury"] == -payment.amount
    assert postings["Assets:ArcTestnet:Recipient"] == payment.amount

    return {
        "payment_id": str(payment_id),
        "transaction_hash": tx_hash,
        "block_number": result.block_number,
        "amount": str(payment.amount),
        "status": result.status,
        "ledger_verified": True,
        "signature_verified": True,
    }

if __name__ == "__main__":
    main()