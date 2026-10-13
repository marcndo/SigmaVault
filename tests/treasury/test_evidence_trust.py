import pytest

from sigmavault.treasury.evidence_trust import (
    require_trusted_source,
    require_authenticated_integration,
)

def test_require_trusted_source_rejects_unknown_source():
    with pytest.raises(
        ValueError,
        match="Untrusted evidence source",
    ):
        require_trusted_source(
            source="unknown_provider",
            trusted_sources=frozenset({"bank_api"}),
        )
        
        
def test_require_trusted_source_accepts_allowlisted_source():
    trusted_sources = frozenset({
        "bank_api",
        "mobile_money_api",
    })

    result = require_trusted_source(
        source="bank_api",
        trusted_sources=trusted_sources,
    )

    assert result is None
    
def test_require_authenticated_integration_rejects_unauthenticated():
    with pytest.raises(
        ValueError,
        match="Integration is not authenticated",
    ):
        require_authenticated_integration(
            authenticated=False,
        )
        
@pytest.mark.parametrize(
    "authenticated",
    [
        1,
        "true",
        "yes",
        None,
        [],
    ],
)
def test_require_authenticated_integration_rejects_non_boolean_values(
    authenticated,
):
    with pytest.raises(
        ValueError,
        match="Integration is not authenticated",
    ):
        require_authenticated_integration(
            authenticated=authenticated,
        )
        
        
def test_require_authenticated_integration_accepts_true():
    result = require_authenticated_integration(
        authenticated=True,
    )

    assert result is None