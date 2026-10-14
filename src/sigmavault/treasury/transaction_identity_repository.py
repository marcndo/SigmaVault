import sqlite3
from contextlib import closing
from pathlib import Path

from sigmavault.treasury.provider_identity import (
    ProviderTransactionIdentity,
)


class SQLiteTransactionIdentityRepository:
    """Persist provider-scoped transaction identities in SQLite."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = database_path

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS processed_transaction_identities (
                        provider_id TEXT NOT NULL,
                        transaction_reference TEXT NOT NULL,
                        UNIQUE (provider_id, transaction_reference)
                    )
                    """
                )

    def record(self, identity: ProviderTransactionIdentity) -> bool:
        """Return True if newly recorded, False if already present."""

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO processed_transaction_identities (
                        provider_id,
                        transaction_reference
                    )
                    VALUES (?, ?)
                    ON CONFLICT (
                        provider_id,
                        transaction_reference
                    ) DO NOTHING
                    """,
                    (
                        identity.provider_id,
                        identity.transaction_reference,
                    ),
                )

                inserted = cursor.rowcount == 1

        return inserted