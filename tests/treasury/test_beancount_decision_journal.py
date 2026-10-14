from datetime import date
from beancount.loader import load_string

from sigmavault.treasury.agent_decision import AgentDecision
from sigmavault.treasury.beancount_decision_journal import (
    render_decision_event,
)


def test_render_decision_event_includes_explanation():
    decision = AgentDecision(
        decision_id="DEC-001",
        outcome="approved",
        explanation="The proposed allocation preserves the required liquidity buffer.",
    )

    result = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    assert result == (
        '2026-10-14 event "SigmaVaultDecision" "DEC-001: approved"\n'
        '  decision_id: "DEC-001"\n'
        '  outcome: "approved"\n'
        '  explanation: "The proposed allocation preserves the required liquidity buffer."\n'
    )
    
def test_render_decision_event_escapes_quotes_in_explanation():
    decision = AgentDecision(
        decision_id="DEC-002",
        outcome="rejected",
        explanation='The policy requires a "minimum cash reserve" of 100,000 XAF.',
    )

    result = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    assert result == (
        '2026-10-14 event "SigmaVaultDecision" "DEC-002: rejected"\n'
        '  decision_id: "DEC-002"\n'
        '  outcome: "rejected"\n'
        '  explanation: "The policy requires a \\"minimum cash reserve\\" of 100,000 XAF."\n'
    )
    
def test_render_decision_event_escapes_backslashes_in_explanation():
    decision = AgentDecision(
        decision_id="DEC-003",
        outcome="deferred",
        explanation=r"Supporting evidence is stored at C:\reports\treasury.txt",
    )

    result = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    assert result == (
        '2026-10-14 event "SigmaVaultDecision" "DEC-003: deferred"\n'
        '  decision_id: "DEC-003"\n'
        '  outcome: "deferred"\n'
        '  explanation: "Supporting evidence is stored at '
        'C:\\\\reports\\\\treasury.txt"\n'
    )
    
def test_render_decision_event_escapes_newlines_in_explanation():
    decision = AgentDecision(
        decision_id="DEC-004",
        outcome="rejected",
        explanation=(
            "The proposed allocation was rejected.\n"
            "Upcoming supplier payments exceed available surplus.\n"
            "The operating cash reserve must be preserved."
        ),
    )

    result = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    assert result == (
        '2026-10-14 event "SigmaVaultDecision" "DEC-004: rejected"\n'
        '  decision_id: "DEC-004"\n'
        '  outcome: "rejected"\n'
        '  explanation: "The proposed allocation was rejected.\\n'
        'Upcoming supplier payments exceed available surplus.\\n'
        'The operating cash reserve must be preserved."\n'
    )
    
    
def test_render_decision_event_escapes_special_characters_in_decision_id():
    decision = AgentDecision(
        decision_id='DEC-"001"\\revision\n2',
        outcome="deferred",
        explanation="Additional evidence is required.",
    )

    result = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    assert result == (
        '2026-10-14 event "SigmaVaultDecision" '
        '"DEC-\\"001\\"\\\\revision\\n2: deferred"\n'
        '  decision_id: "DEC-\\"001\\"\\\\revision\\n2"\n'
        '  outcome: "deferred"\n'
        '  explanation: "Additional evidence is required."\n'
    )
    
    
def test_render_decision_event_is_valid_beancount():
    decision = AgentDecision(
        decision_id="DEC-005",
        outcome="rejected",
        explanation=(
            'The "minimum reserve" requirement was not satisfied.\n'
            r"Supporting evidence: C:\reports\treasury.txt"
        ),
    )

    journal = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    entries, errors, options = load_string(journal)

    assert errors == []
    assert len(entries) == 1

    entry = entries[0]

    assert entry.type == "SigmaVaultDecision"
    assert entry.description == "DEC-005: rejected"
    assert entry.meta["decision_id"] == decision.decision_id
    assert entry.meta["outcome"] == decision.outcome
    assert entry.meta["explanation"] == decision.explanation
    
    
def test_beancount_parser_preserves_special_characters_in_decision_id():
    decision = AgentDecision(
        decision_id='DEC-"001"\\revision\n2',
        outcome="deferred",
        explanation="Additional settlement evidence is required.",
    )

    journal = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    entries, errors, _ = load_string(journal)

    assert errors == []
    assert len(entries) == 1

    entry = entries[0]

    assert entry.type == "SigmaVaultDecision"
    assert entry.description == f"{decision.decision_id}: deferred"
    assert entry.meta["decision_id"] == decision.decision_id
    assert entry.meta["outcome"] == decision.outcome
    assert entry.meta["explanation"] == decision.explanation
    
    

def test_render_decision_event_escapes_carriage_returns():
    decision = AgentDecision(
        decision_id="DEC-007",
        outcome="deferred",
        explanation=(
            "Settlement evidence is incomplete.\r\n"
            "Awaiting confirmation from the payment provider."
        ),
    )

    journal = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    assert (
        'explanation: "Settlement evidence is incomplete.\\r\\n'
        'Awaiting confirmation from the payment provider."\n'
    ) in journal

    entries, errors, _ = load_string(journal)

    assert errors == []
    assert len(entries) == 1
    assert entries[0].meta["explanation"] == decision.explanation
    

import pytest
from beancount.core.data import Event


@pytest.mark.parametrize(
    "outcome",
    ["approved", "rejected", "deferred"],
)
def test_all_decision_outcomes_are_non_posting_beancount_events(
    outcome: str,
):
    decision = AgentDecision(
        decision_id=f"DEC-{outcome.upper()}",
        outcome=outcome,
        explanation=f"The treasury policy returned {outcome}.",
    )

    journal = render_decision_event(
        decision=decision,
        event_date=date(2026, 10, 14),
    )

    entries, errors, _ = load_string(journal)

    assert errors == []
    assert len(entries) == 1

    entry = entries[0]

    assert isinstance(entry, Event)
    assert entry.type == "SigmaVaultDecision"
    assert entry.meta["decision_id"] == decision.decision_id
    assert entry.meta["outcome"] == outcome
    assert entry.meta["explanation"] == decision.explanation
    assert not hasattr(entry, "postings")