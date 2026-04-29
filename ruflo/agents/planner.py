"""Planner agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class PlannerAgent(Agent):
    name = "planner"
    role = "planner"

    async def run(self, ctx: RunContext) -> AgentResult:
        memory_hits = ctx.get("memory_hits", [])
        prompt = f"Plan an SDLC pipeline for: {ctx.goal}\nRelevant memory: {memory_hits}"
        summary = await self.complete(ctx, prompt, purpose="decompose-goal")
        plan = [
            {"id": "architecture", "owner": "architect", "goal": "Define service boundaries and contracts."},
            {"id": "backend", "owner": "backend", "goal": "Build FastAPI telemetry APIs."},
            {"id": "frontend", "owner": "frontend", "goal": "Build React dashboard UI."},
            {"id": "database", "owner": "database", "goal": "Create telemetry schema and migrations."},
            {"id": "review", "owner": "reviewer", "goal": "Review maintainability and correctness."},
            {"id": "security", "owner": "security", "goal": "Scan vulnerabilities and unsafe defaults."},
            {"id": "deployment", "owner": "deployment", "goal": "Package with Docker and Kubernetes."},
        ]
        ctx.set("plan", plan)
        body = dedent(
            f"""
            # Generated SDLC Plan

            Goal: {ctx.goal}

            ## Agent Sequence

            1. Planner decomposes the requested product.
            2. Architect defines services, contracts, and data flow.
            3. Backend agent creates FastAPI telemetry APIs.
            4. Frontend agent builds the React telemetry dashboard.
            5. DB agent creates schema and migration files.
            6. Reviewer validates code shape and maintainability.
            7. Security agent checks unsafe defaults and dependencies.
            8. Deployment agent emits Docker and Kubernetes manifests.

            ## Router Notes

            {summary}
            """
        ).strip() + "\n"
        ctx.add_artifact("PLAN.md", body, producer=self.name, kind="doc")
        return AgentResult(agent=self.name, summary="Created SDLC task plan.", data={"plan": plan})

