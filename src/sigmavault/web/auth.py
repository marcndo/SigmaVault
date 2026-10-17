from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import secrets
import sqlite3

from pwdlib import PasswordHash


SESSION_LIFETIME = timedelta(hours=8)
password_hasher = PasswordHash.recommended()


class AuthenticationService:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(self.database_path)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)

        connection.commit()
        return connection

    def verify_credentials(
        self,
        username: str,
        password: str,
        expected_username: str,
        password_hash: str,
    ) -> bool:
        if not secrets.compare_digest(
            username.encode(),
            expected_username.encode(),
        ):
            return False

        return password_hasher.verify(password, password_hash)

    def create_session(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        token_hash = sha256(token.encode()).hexdigest()

        expires_at = (
            datetime.now(timezone.utc) + SESSION_LIFETIME
        ).isoformat()

        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO auth_sessions (
                    token_hash, username, expires_at
                )
                VALUES (?, ?, ?)
                """,
                (token_hash, username, expires_at),
            )

        return token

    def get_session_username(self, token: str) -> str | None:
        token_hash = sha256(token.encode()).hexdigest()

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT username, expires_at
                FROM auth_sessions
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()

        if row is None:
            return None

        username, expires_at = row

        if datetime.fromisoformat(expires_at) <= datetime.now(
            timezone.utc
        ):
            return None

        return username

    def revoke_session(self, token: str) -> None:
        token_hash = sha256(token.encode()).hexdigest()

        with self._connect() as connection:
            connection.execute(
                "DELETE FROM auth_sessions WHERE token_hash = ?",
                (token_hash,),
            )