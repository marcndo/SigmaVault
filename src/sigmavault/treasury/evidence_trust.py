def require_trusted_source(
    source: str,
    trusted_sources: frozenset[str],
) -> None:
    """Require an evidence source to be on the configured allowlist."""

    if source not in trusted_sources:
        raise ValueError("Untrusted evidence source")
    
def require_authenticated_integration(
    authenticated: bool,
) -> None:
    """Require an integration to report successful authentication."""

    if authenticated is not True:
        raise ValueError("Integration is not authenticated")