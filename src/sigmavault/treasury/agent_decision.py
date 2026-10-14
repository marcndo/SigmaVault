from dataclasses import dataclass


ALLOWED_OUTCOMES = frozenset({
    "approved",
    "rejected",
    "deferred",
})


@dataclass(frozen=True)
class AgentDecision:
    """Represent an agent decision with a human-readable explanation."""

    decision_id: str
    outcome: str
    explanation: str

    def __post_init__(self) -> None:
        if not isinstance(self.decision_id, str) or not self.decision_id.strip():
            raise ValueError("Agent decision ID must not be blank")

        if not isinstance(self.outcome, str) or self.outcome not in ALLOWED_OUTCOMES:
            raise ValueError("Invalid agent decision outcome")

        if not isinstance(self.explanation, str) or not self.explanation.strip():
            raise ValueError("Agent decision explanation must not be blank")