from datetime import date

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.domain import LiquidityPosition
from sigmavault.treasury.signed_decision_record import (
    SignedDecisionRecord,
    create_signed_decision_record,
)
from sigmavault.treasury.signed_decision_repository import (
    SignedDecisionRepository,
)


class TreasuryDecisionService:
    """Create and persist auditable treasury assessments."""

    def __init__(
        self,
        repository: SignedDecisionRepository,
        private_key: Ed25519PrivateKey,
        policy_version: str,
    ) -> None:
        self.repository = repository
        self.private_key = private_key
        self.policy_version = policy_version

    def assess_and_record(
        self,
        decision_id: str,
        position: LiquidityPosition,
        event_date: date,
    ) -> SignedDecisionRecord:
        """Record an assessment without authorizing execution."""

        explanation = (
            f"Forecast liquidity assessment: "
            f"status={position.status.value}; "
            f"deployable_surplus="
            f"{position.deployable_surplus.amount} "
            f"{position.deployable_surplus.currency}. "
            f"Execution deferred pending independently verified "
            f"cash and settlement evidence."
        )

        decision = AgentDecision(
            decision_id=decision_id,
            outcome="deferred",
            explanation=explanation,
        )

        record = create_signed_decision_record(
            decision=decision,
            event_date=event_date,
            policy_version=self.policy_version,
            private_key=self.private_key,
        )

        self.repository.save(record)

        return record