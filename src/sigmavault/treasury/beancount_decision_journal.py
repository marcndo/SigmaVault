from datetime import date

from sigmavault.treasury.agent_decision import AgentDecision

def escape_beancount_string(value: str) -> str:
    """Escape special characters in a Beancount string."""
    return (
        value
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def render_decision_event(
    decision: AgentDecision,
    event_date: date,
) -> str:
    """Render an agent decision as a Beancount event."""

    escaped_decision_id = escape_beancount_string(
        decision.decision_id
    )

    escaped_explanation = escape_beancount_string(
        decision.explanation
    )

    return (
        f'{event_date.isoformat()} event '
        f'"SigmaVaultDecision" "{escaped_decision_id}: {decision.outcome}"\n'
        f'  decision_id: "{escaped_decision_id}"\n'
        f'  outcome: "{decision.outcome}"\n'
        f'  explanation: "{escaped_explanation}"\n'
    )