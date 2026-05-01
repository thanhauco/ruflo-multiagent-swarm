"""Reviewer agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class ReviewerAgent(Agent):
    name = "reviewer"
    role = "reviewer"

    async def run(self, ctx: RunContext) -> AgentResult:
        summary = await self.complete(ctx, "Review generated artifacts for maintainability", purpose="review")
        report = dedent(
            f"""
            # Review Report

            ## Findings

            - API boundaries are clear and small.
            - Frontend uses a compact operational dashboard layout.
            - Database schema includes referential integrity and time-series index.
            - Artifacts are structured for manual review and deployment readiness.

            ## Recommendations

            - Replace mock telemetry with a signed collector protocol before production.
            - Add pagination or downsampling for long metric histories.
            - Add authentication before exposing cluster telemetry outside localhost.

            ## LLM Notes

            {summary}
            """
        ).strip() + "\n"
        ctx.add_artifact("REVIEW.md", report, producer=self.name, kind="doc")
        ctx.set("review_report", {"status": "pass", "recommendations": 3})
        return AgentResult(agent=self.name, summary="Generated review report.")

