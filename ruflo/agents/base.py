"""Base contract for all SDLC agents."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ruflo.core.context import RunContext
from ruflo.llm.router import LLMRouter


@dataclass
class AgentResult:
    agent: str
    summary: str
    data: dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    name: str = "agent"
    role: str = "general"
    weight_cpu: float = 1.0
    weight_gpu: float = 0.0

    def __init__(self, router: LLMRouter) -> None:
        self.router = router

    async def complete(self, ctx: RunContext, instruction: str, *, purpose: str) -> str:
        ctx.emit("llm.request", agent=self.name, role=self.role, purpose=purpose)
        response = await self.router.complete(role=self.role, prompt=instruction)
        ctx.emit("llm.response", agent=self.name, provider=response.provider, tokens=response.tokens)
        ledger = ctx.get("budget_ledger")
        if ledger is not None:
            ctx.emit("budget.update", agent=self.name, **ledger.record(tokens=response.tokens))
        return response.text

    @abstractmethod
    async def run(self, ctx: RunContext) -> AgentResult:
        """Run the agent against a shared context."""
