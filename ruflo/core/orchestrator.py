"""Ruflo-style orchestrator for multi-agent SDLC runs."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass
from typing import Any, Callable

from ruflo.agents import (
    ArchitectAgent,
    BackendAgent,
    DatabaseAgent,
    DeploymentAgent,
    FrontendAgent,
    PlannerAgent,
    ReviewerAgent,
    SecurityAgent,
)
from ruflo.agents.base import Agent
from ruflo.core.context import RunContext
from ruflo.core.dag import TaskGraph, TaskNode
from ruflo.distributed.pool import WorkerPool
from ruflo.governance.budget import BudgetLedger
from ruflo.governance.critic import evaluate_agent_result
from ruflo.llm.router import LLMRouter
from ruflo.memory.graph import GraphMemory
from ruflo.observability.tracing import events_to_spans
from ruflo.scheduler.gpu import GpuScheduler


@dataclass
class RunResult:
    run_id: str
    artifacts: int
    trace_path: str


class Orchestrator:
    def __init__(
        self,
        *,
        router: LLMRouter | None = None,
        memory: GraphMemory | None = None,
        scheduler: GpuScheduler | None = None,
        workers: WorkerPool | None = None,
    ) -> None:
        self.router = router or LLMRouter.from_env()
        self.memory = memory or GraphMemory()
        self.scheduler = scheduler or GpuScheduler()
        self.workers = workers or WorkerPool(concurrency=int(os.getenv("RUFLO_WORKERS", "4")))
        self.agents = self._build_agents()

    def _build_agents(self) -> dict[str, Agent]:
        return {
            "planner": PlannerAgent(self.router),
            "architect": ArchitectAgent(self.router),
            "backend": BackendAgent(self.router),
            "frontend": FrontendAgent(self.router),
            "database": DatabaseAgent(self.router),
            "reviewer": ReviewerAgent(self.router),
            "security": SecurityAgent(self.router),
            "deployment": DeploymentAgent(self.router),
        }

    def build_default_dag(self) -> TaskGraph:
        g = TaskGraph()
        g.add(TaskNode(name="planner", agent="planner"))
        g.add(TaskNode(name="architect", agent="architect", depends_on=["planner"]))
        g.add(TaskNode(name="backend", agent="backend", depends_on=["architect"]))
        g.add(TaskNode(name="frontend", agent="frontend", depends_on=["architect"]))
        g.add(TaskNode(name="database", agent="database", depends_on=["architect"]))
        g.add(TaskNode(name="reviewer", agent="reviewer", depends_on=["backend", "frontend", "database"]))
        g.add(TaskNode(name="security", agent="security", depends_on=["backend", "frontend", "database"]))
        g.add(TaskNode(name="deployment", agent="deployment", depends_on=["reviewer", "security"]))
        return g

    async def _run_node(self, node: TaskNode, ctx: RunContext) -> None:
        agent = self.agents[node.agent]
        ctx.emit("task.started", task=node.name, agent=agent.name)
        async with self.scheduler.lease(task=node.name, gpu_units=node.weight_gpu) as lease:
            ctx.emit("task.lease", task=node.name, gpu_index=lease.gpu_index, gpu_units=lease.gpu_units)

            async def _invoke() -> None:
                result = await agent.run(ctx)
                verdict = evaluate_agent_result(ctx, result)
                ctx.emit(
                    "critic.verdict",
                    task=node.name,
                    agent=agent.name,
                    status=verdict.status,
                    score=verdict.score,
                    notes=verdict.notes,
                )
                ctx.emit("task.completed", task=node.name, agent=agent.name, summary=result.summary)

            await self.workers.submit(_invoke)

    async def run(
        self,
        goal: str,
        *,
        run_id: str | None = None,
        event_hook: Callable[[dict[str, Any]], None] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunResult:
        ctx = RunContext(goal=goal, run_id=run_id or uuid.uuid4().hex[:12], event_hook=event_hook)
        ctx.set("budget_ledger", BudgetLedger())
        if metadata:
            ctx.set("run_metadata", metadata)
        ctx.emit("run.started", goal=goal, metadata=metadata or {})

        hits = self.memory.search(goal, limit=5)
        ctx.set("memory_hits", [{"title": h.title, "tags": h.tags} for h in hits])
        ctx.emit("memory.hit", count=len(hits))

        dag = self.build_default_dag()
        done: set[str] = set()

        while len(done) < len(dag):
            ready = [n for n in dag.ready(done) if n.name not in done]
            if not ready:
                raise RuntimeError("No schedulable task found; DAG may have cycles.")

            await asyncio.gather(*(self._run_node(node, ctx) for node in ready))
            done.update(node.name for node in ready)

        summary = f"Completed run with {len(ctx.artifacts)} artifacts and {len(ctx.events)} events."
        self.memory.remember_run(ctx.run_id, goal, summary, tags=["sdlc", "multi-agent", "ruflo"])
        ctx.emit("memory.write", run_id=ctx.run_id)
        ctx.emit("run.completed", run_id=ctx.run_id)
        spans_path = ctx.run_dir / "trace.otlp.json"
        ctx.emit("observability.export", path=str(spans_path))
        spans_path.write_text(json.dumps(events_to_spans(ctx.run_id, ctx.events), indent=2), encoding="utf-8")
        trace_path = str(ctx.dump_trace())

        return RunResult(run_id=ctx.run_id, artifacts=len(ctx.artifacts), trace_path=trace_path)


