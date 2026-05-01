"""Database agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class DatabaseAgent(Agent):
    name = "database"
    role = "database"

    async def run(self, ctx: RunContext) -> AgentResult:
        await self.complete(ctx, f"Create schema for {ctx.get('architecture', {})}", purpose="database-schema")
        schema = dedent(
            '''
            CREATE TABLE IF NOT EXISTS gpu_devices (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                memory_total_mb INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'unknown',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS gpu_metrics (
                id BIGSERIAL PRIMARY KEY,
                gpu_id TEXT NOT NULL REFERENCES gpu_devices(id),
                sampled_at TIMESTAMPTZ NOT NULL,
                utilization_pct INTEGER NOT NULL CHECK (utilization_pct BETWEEN 0 AND 100),
                memory_used_mb INTEGER NOT NULL CHECK (memory_used_mb >= 0),
                temperature_c INTEGER NOT NULL,
                power_watts INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_gpu_metrics_gpu_time
            ON gpu_metrics (gpu_id, sampled_at DESC);
            '''
        ).strip() + "\n"
        ctx.add_artifact("db/schema.sql", schema, producer=self.name, kind="config")
        ctx.add_artifact("db/migrations/001_init.sql", schema, producer=self.name, kind="config")
        ctx.set("schema", {"tables": ["gpu_devices", "gpu_metrics"]})
        return AgentResult(agent=self.name, summary="Generated PostgreSQL schema.")
