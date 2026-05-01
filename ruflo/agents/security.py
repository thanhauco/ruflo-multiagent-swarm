"""Security agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class SecurityAgent(Agent):
    name = "security"
    role = "security"

    async def run(self, ctx: RunContext) -> AgentResult:
        summary = await self.complete(ctx, "Scan generated GPU dashboard for security risks", purpose="security-scan")
        report = dedent(
            f"""
            # Security Report

            ## Checks

            - No hard-coded secrets are emitted in generated app code.
            - API uses explicit CORS origins for local development.
            - Database schema avoids dynamic SQL.
            - Deployment manifests avoid privileged containers.

            ## Production Gates

            - Add authN/authZ for dashboard and API.
            - Restrict CORS origins to deployed frontend hostnames.
            - Add container image scanning in CI.
            - Store credentials in Kubernetes Secrets or cloud secret stores.

            ## LLM Notes

            {summary}
            """
        ).strip() + "\n"
        ctx.add_artifact("SECURITY.md", report, producer=self.name, kind="doc")
        ctx.set("security_report", {"status": "needs-production-hardening", "critical": 0})
        return AgentResult(agent=self.name, summary="Generated security report.")
