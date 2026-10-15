import sqlite3
from contextlib import closing
from datetime import date
from decimal import Decimal
from pathlib import Path

from sigmavault.treasury.domain import Money
from sigmavault.treasury.upcoming_obligations import UpcomingBill


class SQLiteUpcomingBillRepository:
    """Persistent storage for upcoming financial oobbligations."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS upcoming_bills (
                        bill_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        amount TEXT NOT NULL,
                        currency TEXT NOT NULL,
                        due_date TEXT NOT NULL,
                        status TEXT NOT NULL
                            CHECK (
                                status IN (
                                    'confirmed',
                                    'scheduled',
                                    'estimated'
                                )
                            )
                    )
                    """
                )

    def save(self, bill: UpcomingBill) -> None:
        """Insert a bill. Duplicate IDs are rejected."""

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO upcoming_bills (
                        bill_id,
                        name,
                        amount,
                        currency,
                        due_date,
                        status
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bill.bill_id,
                        bill.name,
                        str(bill.amount.amount),
                        bill.amount.currency,
                        bill.due_date.isoformat(),
                        bill.status,
                    ),
                )

    def list_all(self) -> list[UpcomingBill]:
        """Return all bills ordered by due date."""

        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT
                    bill_id,
                    name,
                    amount,
                    currency,
                    due_date,
                    status
                FROM upcoming_bills
                ORDER BY due_date, bill_id
                """
            ).fetchall()

        return [
            UpcomingBill(
                bill_id=row[0],
                name=row[1],
                amount=Money(
                    amount=Decimal(row[2]),
                    currency=row[3],
                ),
                due_date=date.fromisoformat(row[4]),
                status=row[5],
            )
            for row in rows
        ]

    def delete(self, bill_id: str) -> bool:
        """Return True if a bill was deleted."""

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    DELETE FROM upcoming_bills
                    WHERE bill_id = ?
                    """,
                    (bill_id,),
                )

                return cursor.rowcount == 1