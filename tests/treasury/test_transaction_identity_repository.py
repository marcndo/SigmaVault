import sqlite3
import pytest
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from sigmavault.treasury.provider_identity import (
    ProviderTransactionIdentity,
)
from sigmavault.treasury.transaction_identity_repository import (
    SQLiteTransactionIdentityRepository,
)


def test_repository_records_new_transaction_identity(tmp_path):
    database_path = tmp_path / "transactions.db"

    repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    result = repository.record(identity)

    assert result is True

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM processed_transaction_identities
            WHERE provider_id = ?
              AND transaction_reference = ?
            """,
            ("bank_a", "TXN-001"),
        ).fetchone()[0]

    assert count == 1
    
    
def test_repository_returns_false_for_duplicate_identity(tmp_path):
    database_path = tmp_path / "transactions.db"

    repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    first_result = repository.record(identity)
    second_result = repository.record(identity)

    assert first_result is True
    assert second_result is False

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM processed_transaction_identities
            WHERE provider_id = ?
              AND transaction_reference = ?
            """,
            ("bank_a", "TXN-001"),
        ).fetchone()[0]

    assert count == 1
    
def record(self, identity: ProviderTransactionIdentity) -> bool:
    """Return True if newly recorded, False if already present."""

    with sqlite3.connect(self.database_path) as connection:
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

        return cursor.rowcount == 1
    
    
def test_repository_allows_same_reference_from_different_providers(tmp_path):
    database_path = tmp_path / "transactions.db"

    repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    first = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    second = ProviderTransactionIdentity(
        provider_id="bank_b",
        transaction_reference="TXN-001",
    )

    assert repository.record(first) is True
    assert repository.record(second) is True

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM processed_transaction_identities
            WHERE transaction_reference = ?
            """,
            ("TXN-001",),
        ).fetchone()[0]

    assert count == 2
    
def test_repository_allows_different_references_from_same_provider(
    tmp_path,
):
    database_path = tmp_path / "transactions.db"

    repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    first = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    second = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-002",
    )

    assert repository.record(first) is True
    assert repository.record(second) is True

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM processed_transaction_identities
            WHERE provider_id = ?
            """,
            ("bank_a",),
        ).fetchone()[0]

    assert count == 2
    
    
def test_repository_detects_duplicate_across_instances(tmp_path):
    database_path = tmp_path / "transactions.db"

    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    first_repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    assert first_repository.record(identity) is True

    # Simulate a new repository instance using the same database.
    second_repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    assert second_repository.record(identity) is False

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM processed_transaction_identities
            WHERE provider_id = ?
              AND transaction_reference = ?
            """,
            ("bank_a", "TXN-001"),
        ).fetchone()[0]

    assert count == 1
    
    
def test_repository_prevents_duplicate_concurrent_inserts(tmp_path):
    database_path = tmp_path / "transactions.db"

    repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    barrier = Barrier(2, timeout=5)

    def record_identity():
        barrier.wait()
        return repository.record(identity)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(record_identity)
            for _ in range(2)
        ]

        results = [future.result() for future in futures]

    assert sorted(results) == [False, True]

    with sqlite3.connect(database_path) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM processed_transaction_identities
            WHERE provider_id = ?
              AND transaction_reference = ?
            """,
            ("bank_a", "TXN-001"),
        ).fetchone()[0]

    assert count == 1
    
def test_repository_propagates_database_errors(tmp_path):
    database_path = tmp_path / "transactions.db"

    repository = SQLiteTransactionIdentityRepository(
        database_path=database_path,
    )

    identity = ProviderTransactionIdentity(
        provider_id="bank_a",
        transaction_reference="TXN-001",
    )

    # Simulate an unexpected database failure.
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "DROP TABLE processed_transaction_identities"
        )

    with pytest.raises(
        sqlite3.OperationalError,
        match="no such table",
    ):
        repository.record(identity)