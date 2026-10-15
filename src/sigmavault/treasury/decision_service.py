from datetime import date
from sigmavault.treasury.treasury_agent import TreasuryRecommendation
from sigmavault.treasury.beancount_audit_journal import (
    BeancountAuditJournal,
)

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
        journal: BeancountAuditJournal | None = None,

    ) -> None:
        self.repository = repository
        self.private_key = private_key
        self.policy_version = policy_version
        self.journal = journal

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

        if self.journal is not None:
            self.journal.append(record)
        
        self.repository.save(record)
        
        return record
    
    def record_recommendation(
            self,
            decision_id: str,
            recommendation: TreasuryRecommendation,
            event_date: date,
        ) -> SignedDecisionRecord:
        """Sign and persist the actual advisory agent recommendation."""
    
        if not recommendation.requires_human_review:
            raise ValueError(
                "Pilot recommendations must require human review"
            )
    
        decision = AgentDecision(
            decision_id=decision_id,
            outcome="deferred",
            explanation=(
                f"Agent recommended action: {recommendation.action}. "
                f"Agent explanation: {recommendation.explanation} "
                f"Human review required; execution not authorized."
            ),
        )
    
        record = create_signed_decision_record(
            decision=decision,
            event_date=event_date,
            policy_version=self.policy_version,
            private_key=self.private_key,
        )
    
        if self.journal is None:
            raise RuntimeError(
                "A Beancount journal is required for agent recommendations"
            )
    
        self.journal.append(record)
        self.repository.save(record)
    
        return record