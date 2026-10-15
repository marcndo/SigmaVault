import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)


def load_audit_private_key() -> Ed25519PrivateKey:
    """Load the persistent audit signing key from configuration."""

    pem = os.getenv("SIGMAVAULT_AUDIT_PRIVATE_KEY_PEM")

    if not pem:
        raise RuntimeError(
            "SIGMAVAULT_AUDIT_PRIVATE_KEY_PEM is not configured"
        )

    # Supports a PEM stored in an environment variable with
    # literal newline escapes.
    pem_bytes = pem.replace("\\n", "\n").encode("utf-8")

    key = serialization.load_pem_private_key(
        pem_bytes,
        password=None,
    )

    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Audit signing key must be Ed25519")

    return key