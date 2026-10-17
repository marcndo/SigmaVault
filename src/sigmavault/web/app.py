from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Literal
import os
import sqlite3
import csv
from uuid import uuid4
from sigmavault.treasury.csv_obligations import (
    csv_records_to_upcoming_bills,
)
import io
import httpx
from sigmavault.web.auth import AuthenticationService
from fastapi import FastAPI, HTTPException, Depends, Request, Response, status
from sigmavault.web.auth import AuthenticationService
from sigmavault.integrations.firefly.client import FireflyClient
from sigmavault.pipeline.firefly_adapter import FireflySourceAdapter
from fastapi.responses import StreamingResponse

from sigmavault.treasury.audit_export import create_audit_export

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import UploadFile, File, Form
from sigmavault.pipeline.csv_adapter import CSVSourceAdapter
from sigmavault.pipeline.coordinator import FinancialDataPipeline
from sigmavault.treasury.journal_synchronizer import synchronize_journal

from sigmavault.treasury.audit_key_config import (
    load_audit_private_key,
)
from sigmavault.treasury.beancount_audit_journal import (
    BeancountAuditJournal,
)
from sigmavault.treasury.decision_service import (
    TreasuryDecisionService,
)
from sigmavault.treasury.signed_decision_repository import (
    SQLiteSignedDecisionRepository,
)
from pydantic_ai.models.test import TestModel
from sigmavault.treasury.agent_runner import run_treasury_agent
from sigmavault.integrations.arc.gateway import ArcGateway
from sigmavault.integrations.arc.wallet_snapshot import (
    capture_arc_wallet_snapshot,
)

from sigmavault.treasury.upcoming_bill_repository import (
    SQLiteUpcomingBillRepository,
)



from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from sigmavault.treasury.domain import Money
from sigmavault.treasury.obligation_assessment import (
    assess_upcoming_obligations,
)
from sigmavault.treasury.upcoming_obligations import UpcomingBill

app = FastAPI(
    title="SigmaVault",
    description="AI-assisted treasury management for businesses",
    version="0.1.0",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
DATABASE_PATH = Path(
    os.getenv(
        "SIGMAVAULT_DATABASE_PATH",
        "data/sigmavault_pilot.sqlite3",
    )
)

AUDIT_JOURNAL_PATH = Path(
    os.getenv(
        "SIGMAVAULT_AUDIT_JOURNAL_PATH",
        "data/treasury_decisions.beancount",
    )
)
MAX_CSV_UPLOAD_BYTES = 5 * 1024 * 1024

bill_repository = SQLiteUpcomingBillRepository(DATABASE_PATH)

auth_service = AuthenticationService(DATABASE_PATH)

SESSION_COOKIE = "sigmavault_session"
TESTER_USERNAME = "obsec_tester"


class LoginRequest(BaseModel):
    username: str
    password: str


def require_tester(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    username = auth_service.get_session_username(token)

    if username != TESTER_USERNAME:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return username

class BillInput(BaseModel):
    bill_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    amount: str
    due_date: date
    status: Literal["confirmed", "scheduled", "estimated"]


class AssessmentRequest(BaseModel):
    available_cash: str
    minimum_buffer: str
    as_of: date
    planning_horizon_days: int = Field(default=30, gt=0, le=365)
    bills: list[BillInput] = Field(default_factory=list)


def parse_money(value: str) -> Money:
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise HTTPException(
            status_code=422,
            detail="Invalid monetary amount",
        ) from exc

    if not amount.is_finite() or amount < 0:
        raise HTTPException(
            status_code=422,
            detail="Monetary amounts must be finite and non-negative",
        )

    return Money(amount, "XAF")


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response):
    password_hash = os.getenv(
        "SIGMAVAULT_TESTER_PASSWORD_HASH", ""
    )

    if not password_hash:
        raise HTTPException(
            status_code=503,
            detail="Tester authentication is not configured",
        )

    valid = auth_service.verify_credentials(
        username=payload.username,
        password=payload.password,
        expected_username=TESTER_USERNAME,
        password_hash=password_hash,
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = auth_service.create_session(TESTER_USERNAME)

    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        secure=os.getenv("SIGMAVAULT_COOKIE_SECURE") == "true",
        samesite="strict",
        max_age=8 * 60 * 60,
        path="/",
    )

    return {"username": TESTER_USERNAME}


@app.get("/api/auth/me")
def current_tester(
    username: str = Depends(require_tester),
):
    return {"username": username}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE)

    if token:
        auth_service.revoke_session(token)

    response.delete_cookie(
        key=SESSION_COOKIE,
        path="/",
        samesite="strict",
        secure=os.getenv("SIGMAVAULT_COOKIE_SECURE") == "true",
    )

    return {"logged_out": True}

@app.get("/api/firefly/transactions")
def get_firefly_transactions():
    base_url = os.getenv("FIREFLY_BASE_URL", "").strip()
    token = os.getenv("FIREFLY_TOKEN", "").strip()
    raw_account_id = os.getenv("FIREFLY_ACCOUNT_ID", "").strip()

    if not base_url or not token or not raw_account_id:
        raise HTTPException(
            status_code=503,
            detail="Firefly III connection is not configured",
        )

    try:
        account_id = int(raw_account_id)
        if account_id <= 0:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(
            status_code=503,
            detail="Invalid Firefly III account configuration",
        ) from exc

    try:
        with httpx.Client(
            base_url=base_url,
            timeout=20.0,
        ) as http_client:
            client = FireflyClient(
                http_client=http_client,
                token=token,
            )

            adapter = FireflySourceAdapter(
                client=client,
                account_id=account_id,
                namespace=f"account-{account_id}",
            )

            records = adapter.fetch_records()

    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Could not retrieve valid Firefly III transactions",
        ) from exc

    return {
        "source": "firefly",
        "account_id": account_id,
        "record_count": len(records),
        "records": [
            {
                "transaction_id": record.identity.record_id,
                "description": record.description,
                "category": record.category,
                "amount": str(record.amount),
                "currency": record.currency,
                "direction": record.direction,
                "transaction_date": (
                    record.transaction_date.isoformat()
                    if record.transaction_date else None
                ),
                "status": record.status,
            }
            for record in records
        ],
    }


@app.post("/api/assess")
def assess(request: AssessmentRequest):
    try:
        bills = bill_repository.list_all()

        assessment = assess_upcoming_obligations(
            bills=bills,
            forecasts=[],
            available_cash=parse_money(request.available_cash),
            minimum_buffer=parse_money(request.minimum_buffer),
            planning_horizon=timedelta(
                days=request.planning_horizon_days
            ),
            as_of=request.as_of,
        )

    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    position = assessment.position

    return {
        "currency": "XAF",
        "available_cash": str(position.available_cash.amount),
        "required_liquidity": str(position.required_liquidity.amount),
        "minimum_buffer": str(position.minimum_cash_buffer.amount),
        "deployable_surplus": str(position.deployable_surplus.amount),
        "liquidity_shortfall": str(position.liquidity_shortfall.amount),
        "status": position.status.value,
        "obligations_count": assessment.obligations_count,
        "forecast_coverage_available": assessment.forecast_coverage_available,
        "requires_human_review": assessment.requires_human_review,
        "execution_authorized": False,
        "cash_source": "user_supplied_unverified",
    }
    
    
@app.get("/api/bills")
def list_bills():
    return [
        {
            "bill_id": bill.bill_id,
            "name": bill.name,
            "amount": str(bill.amount.amount),
            "currency": bill.amount.currency,
            "due_date": bill.due_date.isoformat(),
            "status": bill.status,
        }
        for bill in bill_repository.list_all()
    ]


@app.post("/api/bills", status_code=201)
def create_bill(request: BillInput):
    try:
        bill = UpcomingBill(
            bill_id=request.bill_id,
            name=request.name,
            amount=parse_money(request.amount),
            due_date=request.due_date,
            status=request.status,
        )

        bill_repository.save(bill)

    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="A bill with this ID already exists",
        ) from exc

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "bill_id": bill.bill_id,
        "saved": True,
    }


@app.delete("/api/bills/{bill_id}")
def delete_bill(bill_id: str):
    deleted = bill_repository.delete(bill_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Bill not found",
        )

    return {"deleted": True}

@app.post("/api/agent/recommend")
def recommend(request: AssessmentRequest):
    """
    Generate an advisory recommendation and persist a signed audit record.

    Financial execution is never authorized.
    """
    try:
        bills = bill_repository.list_all()

        assessment = assess_upcoming_obligations(
            bills=bills,
            forecasts=[],
            available_cash=parse_money(request.available_cash),
            minimum_buffer=parse_money(request.minimum_buffer),
            planning_horizon=timedelta(
                days=request.planning_horizon_days
            ),
            as_of=request.as_of,
        )

        recommendation = run_treasury_agent(
            assessment.position,
            evidence_verified=False,
            model=TestModel(),
        )

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    # Audit signing must use the same persistent key across restarts.
    try:
        private_key = load_audit_private_key()

    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Treasury audit signing is not configured",
        ) from exc

    decision_id = f"AGENT-{uuid4().hex}"

    journal = BeancountAuditJournal(
        path=AUDIT_JOURNAL_PATH,
        public_key=private_key.public_key(),
    )

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DATABASE_PATH)
    
    try:
        repository = SQLiteSignedDecisionRepository(connection)
    
        service = TreasuryDecisionService(
            repository=repository,
            private_key=private_key,
            policy_version="pilot-v1",
            journal=journal,
        )
    
        record = service.record_recommendation(
            decision_id=decision_id,
            recommendation=recommendation,
            event_date=request.as_of,
        )
    
        # First, durably commit the signed decision.
        connection.commit()
    
        # Then synchronize the committed decision to Beancount.
        synchronize_journal(
            connection=connection,
            journal_path=AUDIT_JOURNAL_PATH,
            public_key=private_key.public_key(),
        )
    
    except Exception:
        connection.rollback()
        raise
    
    finally:
        connection.close()
    return {
        "decision_id": decision_id,
        "action": recommendation.action,
        "explanation": recommendation.explanation,
        "requires_human_review": recommendation.requires_human_review,
        "execution_authorized": False,
        "model_mode": "Pydantic AI TestModel (demonstration)",
        "forecast_coverage_available": assessment.forecast_coverage_available,
        "audit": {
            "signed": True,
            "signature_algorithm": "Ed25519",
            "journal_format": "Beancount",
            "journal_sha256": record.payload.journal_sha256,
            "policy_version": record.payload.policy_version,
        },
    }
@app.get("/api/arc/wallet")
def get_arc_wallet():
    rpc_url = os.getenv("ARC_RPC_URL")
    wallet_address = os.getenv("ARC_WALLET_ADDRESS")

    if not rpc_url or not wallet_address:
        raise HTTPException(
            status_code=503,
            detail="Arc wallet observation is not configured",
        )

    try:
        gateway = ArcGateway(rpc_url=rpc_url)

        snapshot = capture_arc_wallet_snapshot(
            gateway=gateway,
            address=wallet_address,
        )

    except (ValueError, ConnectionError, TimeoutError):
        raise HTTPException(
            status_code=503,
            detail="Arc wallet observation is temporarily unavailable",
        )

    return {
        "network": "Arc Testnet",
        "chain_id": snapshot.chain_id,
        "block_number": snapshot.block_number,
        "native_usdc_balance": str(snapshot.native_usdc_balance),
        "currency": "USDC",
        "observed_at": snapshot.observed_at.isoformat(),
        "execution_authorized": False,
    }
    
    
@app.post("/api/csv/preview")
def preview_csv(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="A CSV file is required",
        )

    with TemporaryDirectory() as directory:
        path = Path(directory) / "upload.csv"

        uploaded_bytes = 0

        with path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                uploaded_bytes += len(chunk)

                if uploaded_bytes > MAX_CSV_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="CSV file is too large",
                    )

                destination.write(chunk)

        try:
            source = CSVSourceAdapter(
                path=path,
                namespace="csv-preview",
            )

            result = FinancialDataPipeline().process(source)
            records = result.records

        except (ValueError, UnicodeError, csv.Error) as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

    return {
        "valid": True,
        "record_count": len(records),
        "records": [
            {
                "record_id": record.identity.record_id,
                "description": record.description,
                "category": record.category,
                "amount": str(record.amount),
                "currency": record.currency,
                "record_type": record.direction,
                "transaction_date": (
                    record.transaction_date.isoformat()
                    if record.transaction_date
                    else None
                ),
                "due_date": (
                    record.due_date.isoformat()
                    if record.due_date
                    else None
                ),
                "status": record.status,
                "source": record.source,
            }
            for record in records
        ],
    }
    
@app.post("/api/csv/assess")
def assess_csv(
    file: UploadFile = File(...),
    available_cash: str = Form(...),
    minimum_buffer: str = Form(...),
    as_of: date = Form(...),
    planning_horizon_days: int = Form(30),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=422,
            detail="A CSV file is required",
        )

    if not 1 <= planning_horizon_days <= 365:
        raise HTTPException(
            status_code=422,
            detail="Planning horizon must be between 1 and 365 days",
        )

    cash = parse_money(available_cash)
    buffer = parse_money(minimum_buffer)

    with TemporaryDirectory() as directory:
        path = Path(directory) / "upload.csv"
        uploaded_bytes = 0

        with path.open("wb") as destination:
            while chunk := file.file.read(1024 * 1024):
                uploaded_bytes += len(chunk)

                if uploaded_bytes > MAX_CSV_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail="CSV file is too large",
                    )

                destination.write(chunk)

        try:
            source = CSVSourceAdapter(
                path=path,
                namespace="csv-assessment",
            )

            records = FinancialDataPipeline().process(source).records
            bills = csv_records_to_upcoming_bills(records)

            assessment = assess_upcoming_obligations(
                bills=bills,
                forecasts=[],
                available_cash=cash,
                minimum_buffer=buffer,
                planning_horizon=timedelta(
                    days=planning_horizon_days,
                ),
                as_of=as_of,
            )

        except (ValueError, UnicodeError, csv.Error) as exc:
            raise HTTPException(
                status_code=422,
                detail=str(exc),
            ) from exc

    position = assessment.position

    return {
        "currency": "XAF",
        "source": "uploaded_csv",
        "record_count": len(records),
        "eligible_bill_count": len(bills),
        "obligations_count": assessment.obligations_count,
        "available_cash": str(position.available_cash.amount),
        "required_liquidity": str(position.required_liquidity.amount),
        "minimum_buffer": str(position.minimum_cash_buffer.amount),
        "deployable_surplus": str(position.deployable_surplus.amount),
        "liquidity_shortfall": str(position.liquidity_shortfall.amount),
        "status": position.status.value,
        "forecast_coverage_available": False,
        "requires_human_review": True,
        "execution_authorized": False,
        "cash_source": "user_supplied_unverified",
    }
    
@app.get("/api/audit/download")
def download_signed_audit():
    """Download verified, signed treasury decision artifacts."""

    try:
        private_key = load_audit_private_key()
    except (RuntimeError, ValueError):
        raise HTTPException(
            status_code=503,
            detail="Treasury audit signing is not configured",
        )

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        exported = create_audit_export(
            connection=connection,
            journal_path=AUDIT_JOURNAL_PATH,
            public_key=private_key.public_key(),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail="Audit export unavailable: verification failed or no signed decisions exist",
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail="Audit export unavailable: journal reconciliation failed",
        ) from exc

    finally:
        connection.close()

    return StreamingResponse(
        io.BytesIO(exported),
        media_type="application/zip",
        headers={
            "Content-Disposition":
                'attachment; filename="sigmavault-audit-export.zip"'
        },
    )