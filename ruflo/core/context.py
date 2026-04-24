"""Run-scoped context shared across agents."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


@dataclass
class Artifact:
    """A single file produced by an agent."""

    path: str          # relative path inside the run output dir
    content: str
    producer: str      # agent name
    kind: str = "code"  # code | doc | config | manifest


@dataclass
class RunContext:
    """Shared blackboard for one swarm run."""

    goal: str
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    out_dir: Path = field(default_factory=lambda: Path(os.getenv("RUFLO_OUT_DIR", "./out")))
    blackboard: dict[str, Any] = field(default_factory=dict)
    artifacts: list[Artifact] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    event_hook: Callable[[dict[str, Any]], None] | None = None

    @property
    def run_dir(self) -> Path:
        d = self.out_dir / self.run_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    # --- blackboard helpers -------------------------------------------------
    def set(self, key: str, value: Any) -> None:
        self.blackboard[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.blackboard.get(key, default)

    # --- artifacts ----------------------------------------------------------
    def add_artifact(self, path: str, content: str, producer: str, kind: str = "code") -> Artifact:
        art = Artifact(path=path, content=content, producer=producer, kind=kind)
        self.artifacts.append(art)
        full = self.run_dir / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        return art

    # --- events / trace -----------------------------------------------------
    def emit(self, event: str, **payload: Any) -> None:
        rec = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        self.events.append(rec)
        if self.event_hook:
            self.event_hook(rec)

    def dump_trace(self) -> Path:
        p = self.run_dir / "trace.json"
        p.write_text(
            json.dumps(
                {
                    "run_id": self.run_id,
                    "goal": self.goal,
                    "started_at": self.started_at,
                    "events": self.events,
                    "artifacts": [a.__dict__ for a in self.artifacts],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return p
