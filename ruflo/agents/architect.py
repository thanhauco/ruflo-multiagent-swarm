"""Architect agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class ArchitectAgent(Agent):
    name = "architect"
    role = "architect"

    async def run(self, ctx: RunContext) -> AgentResult:
        plan = ctx.get("plan", [])
        prompt = f"Design a FastAPI + React GPU telemetry platform for {ctx.goal}. Plan: {plan}"
        summary = await self.complete(ctx, prompt, purpose="design-architecture")
        architecture = {
            "services": ["api", "web", "postgres", "prometheus-compatible-metrics"],
            "api": ["GET /health", "GET /api/gpus", "GET /api/gpus/{id}/metrics"],
            "frontend": ["GPU summary cards", "utilization table", "temperature and memory chart"],
            "storage": "PostgreSQL tables for gpu_devices and gpu_metrics",
        }
        ctx.set("architecture", architecture)
        doc = dedent(
            f"""
            # Generated Application Architecture

            Goal: {ctx.goal}

            ## Services

            - `api`: FastAPI service exposing GPU telemetry endpoints.
            - `web`: React dashboard consuming the API.
            - `postgres`: Stores historical GPU device and metric samples.
            - `metrics`: Prometheus-compatible scraping surface for operations.

            ## API Contracts

            - `GET /health` returns service health.
            - `GET /api/gpus` returns known GPU devices and latest samples.
            - `GET /api/gpus/{{gpu_id}}/metrics` returns historical metrics.

            ## Data Flow

            Telemetry collectors publish samples to the API. The API persists
            device metadata and metric samples, then serves aggregated views to
            the React dashboard.

            ## LLM Notes

            {summary}
            """
        ).strip() + "\n"
        diagram = dedent(
            """
            flowchart LR
                Collector[GPU collectors] --> API[FastAPI API]
                API --> DB[(PostgreSQL)]
                API --> Metrics[Prometheus metrics]
                Web[React dashboard] --> API
            """
        ).strip() + "\n"
        ctx.add_artifact("ARCHITECTURE.md", doc, producer=self.name, kind="doc")
        ctx.add_artifact("diagram.mmd", diagram, producer=self.name, kind="doc")
        return AgentResult(agent=self.name, summary="Defined service architecture.", data=architecture)
