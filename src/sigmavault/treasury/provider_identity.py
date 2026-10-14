from dataclasses import dataclass

from sigmavault.treasury.provider_reference import (
    require_provider_reference,
)


@dataclass(frozen=True)
class ProviderTransactionIdentity:
    """Identify a transaction within a provider's namespace."""

    provider_id: str
    transaction_reference: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.provider_id, str)
            or not self.provider_id.strip()
        ):
            raise ValueError("Provider ID must not be blank")

        require_provider_reference(self.transaction_reference)