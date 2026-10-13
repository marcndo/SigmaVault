import pytest

from sigmavault.treasury.provider_reference import (
    require_provider_reference,
)


@pytest.mark.parametrize(
    "reference",
    ["", " ", "\t", "\n"],
)
def test_provider_reference_rejects_blank_values(reference):
    with pytest.raises(
        ValueError,
        match="Provider reference must not be blank",
    ):
        require_provider_reference(reference)
        

@pytest.mark.parametrize(
    "reference",
    [
        "BANK-TXN-001",
        "MTN-MOMO-2026-12345",
        "ORANGE-MONEY-98765",
    ],
)
def test_provider_reference_accepts_valid_values(reference):
    result = require_provider_reference(reference)

    assert result is None
    

@pytest.mark.parametrize(
    "reference",
    [
        None,
        12345,
        True,
        12.5,
        [],
        {},
    ],
)
def test_provider_reference_rejects_non_string_values(reference):
    with pytest.raises(
        ValueError,
        match="Provider reference must not be blank",
    ):
        require_provider_reference(reference)