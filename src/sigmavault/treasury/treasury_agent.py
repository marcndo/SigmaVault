from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext


@dataclass(frozen=True)
class TreasuryAgentContext:
    status: str
    deployable_surplus: Decimal
    liquidity_shortfall: Decimal
    currency: str
    evidence_verified: bool


class TreasuryRecommendation(BaseModel):
    action: Literal[
        "preserve_liquidity",
        "investigate",
        "propose_payment",
    ]
    explanation: str = Field(min_length=1)
    requires_human_review: bool = True


treasury_agent = Agent(
    deps_type=TreasuryAgentContext,
    output_type=TreasuryRecommendation,
    instructions=(
        "You are SigmaVault, an AI treasury analyst. "
        "You must call inspect_treasury_position before recommending "
        "any action. "
        "Treat forecasts as planning information, not verified cash. "
        "Never claim a payment was executed. "
        "Never request private keys. "
        "If evidence is unverified, preserve liquidity and recommend "
        "human review. "
        "If there is a liquidity shortfall, preserve liquidity. "
        "You may propose actions but cannot authorize execution."
    ),
)


@treasury_agent.tool
def inspect_treasury_position(
    ctx: RunContext[TreasuryAgentContext],
) -> dict:
    """Return the treasury position and evidence status."""

    position = ctx.deps

    return {
        "status": position.status,
        "deployable_surplus": str(position.deployable_surplus),
        "liquidity_shortfall": str(position.liquidity_shortfall),
        "currency": position.currency,
        "evidence_verified": position.evidence_verified,
        "execution_authorized": False,
    }