"""Small JSON-backed GraphRAG memory layer."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class MemoryRecord:
    kind: str
    title: str
    body: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class GraphMemory:
    """A GraphRAG-shaped memory store with a JSON fallback implementation."""

    def __init__(self, path: Path | str = ".ruflo-memory.json") -> None:
        self.path = Path(path)
        self.records: list[MemoryRecord] = []
        self.edges: list[dict[str, str]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = [MemoryRecord(**r) for r in raw.get("records", [])]
        self.edges = list(raw.get("edges", []))

    def save(self) -> None:
        self.path.write_text(
            json.dumps(
                {"records": [asdict(r) for r in self.records], "edges": self.edges},
                indent=2,
            ),
            encoding="utf-8",
        )

    def add(self, record: MemoryRecord) -> None:
        self.records.append(record)
        self.save()

    def link(self, source: str, relation: str, target: str) -> None:
        self.edges.append({"source": source, "relation": relation, "target": target})
        self.save()

    def search(self, query: str, limit: int = 5) -> list[MemoryRecord]:
        terms = {t.lower() for t in query.split() if len(t) > 2}
        scored: list[tuple[int, MemoryRecord]] = []
        for rec in self.records:
            haystack = " ".join([rec.kind, rec.title, rec.body, *rec.tags]).lower()
            score = sum(1 for term in terms if term in haystack)
            if score:
                scored.append((score, rec))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [rec for _, rec in scored[:limit]]

    def remember_run(self, run_id: str, goal: str, summary: str, tags: list[str]) -> None:
        self.add(
            MemoryRecord(
                kind="Run",
                title=f"Run {run_id}",
                body=summary,
                tags=tags,
                metadata={"run_id": run_id, "goal": goal},
            )
        )
