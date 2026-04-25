"""Lightweight DAG used by the orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import networkx as nx


@dataclass
class TaskNode:
    name: str
    agent: str
    depends_on: list[str] = field(default_factory=list)
    weight_gpu: float = 0.0   # gpu units required (0 => CPU)
    weight_cpu: float = 1.0


class TaskGraph:
    def __init__(self) -> None:
        self._g: nx.DiGraph = nx.DiGraph()

    def add(self, node: TaskNode) -> None:
        self._g.add_node(node.name, data=node)
        for dep in node.depends_on:
            self._g.add_edge(dep, node.name)

    def node(self, name: str) -> TaskNode:
        return self._g.nodes[name]["data"]

    def ready(self, done: set[str]) -> list[TaskNode]:
        out: list[TaskNode] = []
        for n in self._g.nodes:
            if n in done:
                continue
            preds = set(self._g.predecessors(n))
            if preds.issubset(done):
                out.append(self.node(n))
        return out

    def __iter__(self) -> Iterable[TaskNode]:
        for n in nx.topological_sort(self._g):
            yield self.node(n)

    def __len__(self) -> int:
        return self._g.number_of_nodes()
