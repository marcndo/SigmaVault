import pytest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.audit_key_config import (
    load_audit_private_key,
)


def test_loads_existing_ed25519_key(monkeypatch):
    original_key = Ed25519PrivateKey.generate()

    pem = original_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    monkeypatch.setenv(
        "SIGMAVAULT_AUDIT_PRIVATE_KEY_PEM",
        pem.replace("\n", "\\n"),
    )

    loaded_key = load_audit_private_key()

    assert (
        loaded_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        ==
        original_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    )


def test_missing_key_fails_closed(monkeypatch):
    monkeypatch.delenv(
        "SIGMAVAULT_AUDIT_PRIVATE_KEY_PEM",
        raising=False,
    )

    with pytest.raises(RuntimeError):
        load_audit_private_key()


def test_invalid_key_is_rejected(monkeypatch):
    monkeypatch.setenv(
        "SIGMAVAULT_AUDIT_PRIVATE_KEY_PEM",
        "not-a-valid-private-key",
    )

    with pytest.raises(ValueError):
        load_audit_private_key()