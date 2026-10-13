from dataclasses import dataclass


from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionProvenance:
    transaction_id: str
    source: str
    verified: bool

    def __post_init__(self) -> None:
        if (
            not isinstance(self.transaction_id, str)
            or not self.transaction_id.strip()
        ):
            raise ValueError("Invalid transaction ID")
        if (
        not isinstance(self.source, str)
        or not self.source.strip()
        ):
            raise ValueError("Invalid provenance source")
        if type(self.verified) is not bool:
            raise ValueError("Invalid verification status")