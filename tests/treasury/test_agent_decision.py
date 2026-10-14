import pytest
from dataclasses import FrozenInstanceError

from sigmavault.treasury.agent_decision import AgentDecision


def test_agent_decision_stores_required_fields():
    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The proposed allocation preserves the required liquidity buffer.",
    )

    assert decision.decision_id == "DEC-001"
    assert decision.outcome == "approved"
    assert decision.explanation == (
        "The proposed allocation preserves the required liquidity buffer."
    )


@pytest.mark.parametrize(
    "invalid_explanation",
    ["", "   ", None, 123],
)
def test_agent_decision_rejects_invalid_explanation(invalid_explanation):
    with pytest.raises(ValueError, match="explanation"):
        AgentDecision(
            decision_id="DEC-001",
            outcome="approved",
            explanation=invalid_explanation,
        )
        
@pytest.mark.parametrize(
    "invalid_decision_id",
    ["", "   ", None, 123],
)
def test_agent_decision_rejects_invalid_decision_id(invalid_decision_id):
    with pytest.raises(ValueError, match="decision ID"):
        AgentDecision(
            decision_id=invalid_decision_id,
            outcome="approved",
            explanation="The allocation preserves the required liquidity buffer.",
        )
        
@pytest.mark.parametrize(
    "valid_outcome",
    ["approved", "rejected", "deferred"],
)
def test_agent_decision_accepts_valid_outcomes(valid_outcome):
    decision = AgentDecision(
        decision_id="DEC-001",
        outcome=valid_outcome,
        explanation="The treasury policy evaluation has completed.",
    )

    assert decision.outcome == valid_outcome


@pytest.mark.parametrize(
    "invalid_outcome",
    ["", "   ", "executed", "pending", "APPROVED", None, 123],
)
def test_agent_decision_rejects_invalid_outcomes(invalid_outcome):
    with pytest.raises(ValueError, match="outcome"):
        AgentDecision(
            decision_id="DEC-001",
            outcome=invalid_outcome,
            explanation="The treasury policy evaluation has completed.",
        )
        
        
@pytest.mark.parametrize(
    "invalid_outcome",
    [
        [],
        ["approved"],
        {},
        {"outcome": "approved"},
    ],
)
def test_agent_decision_rejects_unhashable_outcomes(invalid_outcome):
    with pytest.raises(ValueError, match="outcome"):
        AgentDecision(
            decision_id="DEC-001",
            outcome=invalid_outcome,
            explanation="The treasury policy evaluation has completed.",
        )
        
def test_agent_decision_is_immutable():
    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The allocation preserves the required liquidity buffer.",
    )

    with pytest.raises(FrozenInstanceError):
        decision.explanation = "Changed explanation"

    with pytest.raises(FrozenInstanceError):
        decision.outcome = "rejected"

    with pytest.raises(FrozenInstanceError):
        decision.decision_id = "DEC-002"