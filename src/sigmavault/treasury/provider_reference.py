def require_provider_reference(reference: str) -> None:
    """Require a nonblank external provider transaction reference."""

    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("Provider reference must not be blank")