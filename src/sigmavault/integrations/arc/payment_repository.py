import sqlite3
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sigmavault.integrations.arc.payment_authorization import (
    PaymentAuthorization,
    PaymentStatus,
)


class PaymentRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

        with self._connect() as connection:
            # First table: payment records
            connection.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    chain_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    transaction_hash TEXT
                )
            """)

            # Second table: prepared blockchain transactions
            connection.execute("""
                CREATE TABLE IF NOT EXISTS prepared_transactions (
                    payment_id TEXT PRIMARY KEY,
                    transaction_hash TEXT NOT NULL UNIQUE,
                    raw_transaction TEXT NOT NULL,
                    FOREIGN KEY (payment_id)
                        REFERENCES payments(payment_id)
                )
            """)

    def _connect(self):
        return sqlite3.connect(self.database_path, timeout=10)

    def create(self, payment: PaymentAuthorization) -> None:
        if payment.status != PaymentStatus.APPROVED:
            raise ValueError("New payments must be approved")

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO payments (
                    payment_id, sender, recipient,
                    amount, chain_id, status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(payment.payment_id),
                    payment.sender,
                    payment.recipient,
                    str(payment.amount),
                    payment.chain_id,
                    payment.status.value,
                ),
            )

    def get(self, payment_id: UUID) -> PaymentAuthorization | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payment_id, sender, recipient,
                       amount, chain_id, status
                FROM payments
                WHERE payment_id = ?
                """,
                (str(payment_id),),
            ).fetchone()

        if row is None:
            return None

        return PaymentAuthorization(
            payment_id=UUID(row[0]),
            sender=row[1],
            recipient=row[2],
            amount=Decimal(row[3]),
            chain_id=row[4],
            status=PaymentStatus(row[5]),
        )

    def claim_for_execution(self, payment_id: UUID) -> bool:
        """Atomically claim an approved payment exactly once."""
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payments
                SET status = ?
                WHERE payment_id = ?
                  AND status = ?
                """,
                (
                    PaymentStatus.BROADCASTING.value,
                    str(payment_id),
                    PaymentStatus.APPROVED.value,
                ),
            )
            return cursor.rowcount == 1

    def record_transaction_hash(
        self, payment_id: UUID, transaction_hash: str
    ) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payments
                SET transaction_hash = ?
                WHERE payment_id = ?
                  AND status = ?
                  AND transaction_hash IS NULL
                """,
                (
                    transaction_hash,
                    str(payment_id),
                    PaymentStatus.BROADCASTING.value,
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError("Cannot record transaction hash")

    def confirm(self, payment_id: UUID) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payments
                SET status = ?
                WHERE payment_id = ?
                  AND status = ?
                  AND transaction_hash IS NOT NULL
                """,
                (
                    PaymentStatus.CONFIRMED.value,
                    str(payment_id),
                    PaymentStatus.BROADCASTING.value,
                ),
            )

            if cursor.rowcount != 1:
                raise ValueError("Payment cannot be confirmed")
            
    def prepare_transaction(
    self,
    payment_id: UUID,
    transaction_hash: str,
    raw_transaction: str,
    ) -> None:
        """Persist a signed transaction before broadcasting."""
        if not transaction_hash.startswith("0x"):
            raise ValueError("Invalid transaction hash")
    
        if not raw_transaction.startswith("0x"):
            raise ValueError("Invalid signed transaction")
    
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE payments
                SET transaction_hash = ?
                WHERE payment_id = ?
                  AND status = ?
                  AND transaction_hash IS NULL
                """,
                (
                    transaction_hash,
                    str(payment_id),
                    PaymentStatus.BROADCASTING.value,
                ),
            )
    
            if cursor.rowcount != 1:
                raise ValueError("Payment cannot be prepared")
    
            connection.execute(
                """
                INSERT INTO prepared_transactions (
                    payment_id, transaction_hash, raw_transaction
                )
                VALUES (?, ?, ?)
                """,
                (
                    str(payment_id),
                    transaction_hash,
                    raw_transaction,
                ),
            )


    def get_prepared_transaction(
        self,
        payment_id: UUID,
    ) -> tuple[str, str] | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT transaction_hash, raw_transaction
                FROM prepared_transactions
                WHERE payment_id = ?
                """,
                (str(payment_id),),
            ).fetchone()
    
        return row
    