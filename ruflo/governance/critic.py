"""Lightweight verifier for agent outputs."""
from __future__ import annotations

from dataclasses import dataclass

from ruflo.agents.base import AgentResult
from ruflo.core.context import RunContext


@dataclass(frozen=True)
class CriticVerdict:
    agent: str
    status: str
    score: float
    notes: list[str]


def evaluate_agent_result(ctx: RunContext, result: AgentResult) -> CriticVerdict:
    notes: list[str] = []
    score = 1.0

    if not result.summary.strip():
        notes.append("Missing summary.")
        score -= 0.35
    if result.agent != result.agent.lower():
        notes.append("Agent id should be lowercase for trace consistency.")
        score -= 0.15

    artifact_count = len(ctx.artifacts)
    if artifact_count == 0 and result.agent not in {"planner", "architect"}:
        notes.append("No artifacts have been produced yet.")
        score -= 0.2

    status = "pass" if score >= 0.75 else "review"
    if not notes:
        notes.append("Output passed deterministic verifier checks.")
    return CriticVerdict(agent=result.agent, status=status, score=round(max(score, 0.0), 2), notes=notes)
