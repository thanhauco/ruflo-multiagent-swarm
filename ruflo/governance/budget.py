"""Token and cost budget accounting for Ruflo runs."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


DEFAULT_USD_PER_1K_TOKENS = float(os.getenv("RUFLO_USD_PER_1K_TOKENS", "0.003"))


@dataclass
class BudgetLedger:
    limit_usd: float = field(default_factory=lambda: float(os.getenv("RUFLO_BUDGET_USD", "1.00")))
    usd_per_1k_tokens: float = field(default_factory=lambda: DEFAULT_USD_PER_1K_TOKENS)
    tokens: int = 0
    estimated_usd: float = 0.0

    def record(self, *, tokens: int) -> dict[str, float | int | str]:
        self.tokens += max(tokens, 0)
        self.estimated_usd = round((self.tokens / 1000) * self.usd_per_1k_tokens, 6)
        status = "ok" if self.estimated_usd <= self.limit_usd else "over_budget"
        return {
            "tokens": self.tokens,
            "estimated_usd": self.estimated_usd,
            "limit_usd": self.limit_usd,
            "status": status,
        }
