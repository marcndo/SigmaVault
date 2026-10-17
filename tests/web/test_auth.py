from datetime import datetime, timedelta, timezone
from hashlib import sha256
import sqlite3

from pwdlib import PasswordHash

from sigmavault.web.auth import AuthenticationService


def test_valid_credentials_are_accepted(tmp_path):
    service = AuthenticationService(tmp_path / "auth.sqlite3")

    password_hash = PasswordHash.recommended().hash(
        "test-password"
    )

    assert service.verify_credentials(
        username="obsec_tester",
        password="test-password",
        expected_username="obsec_tester",
        password_hash=password_hash,
    )


def test_invalid_credentials_are_rejected(tmp_path):
    service = AuthenticationService(tmp_path / "auth.sqlite3")

    password_hash = PasswordHash.recommended().hash(
        "test-password"
    )

    assert not service.verify_credentials(
        username="obsec_tester",
        password="wrong-password",
        expected_username="obsec_tester",
        password_hash=password_hash,
    )


def test_session_can_be_created_and_verified(tmp_path):
    service = AuthenticationService(tmp_path / "auth.sqlite3")

    token = service.create_session("obsec_tester")

    assert service.get_session_username(token) == "obsec_tester"


def test_unknown_session_is_rejected(tmp_path):
    service = AuthenticationService(tmp_path / "auth.sqlite3")

    assert service.get_session_username("invalid-token") is None


def test_logout_revokes_session(tmp_path):
    service = AuthenticationService(tmp_path / "auth.sqlite3")

    token = service.create_session("obsec_tester")

    service.revoke_session(token)

    assert service.get_session_username(token) is None


def test_expired_session_is_rejected(tmp_path):
    database_path = tmp_path / "auth.sqlite3"
    service = AuthenticationService(database_path)

    token = service.create_session("obsec_tester")

    expired_at = (
        datetime.now(timezone.utc) - timedelta(minutes=1)
    ).isoformat()

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE auth_sessions
            SET expires_at = ?
            WHERE token_hash = ?
            """,
            (expired_at, sha256(token.encode()).hexdigest()),
        )

    assert service.get_session_username(token) is None