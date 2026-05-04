"""Feature registry for the 2026 Ruflo platform roadmap."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PlatformFeature:
    name: str
    category: str
    status: str
    description: str


FEATURES_2026: tuple[PlatformFeature, ...] = (
    PlatformFeature(
        name="critic-verifier-loop",
        category="agent intelligence",
        status="implemented",
        description="Runs a deterministic verifier after each agent and emits critic verdict events.",
    ),
    PlatformFeature(
        name="reasoning-replay-branching",
        category="agent intelligence",
        status="implemented",
        description="Forks prior runs into replay branches with source run and event lineage metadata.",
    ),
    PlatformFeature(
        name="cost-budget-ledger",
        category="distributed scale",
        status="implemented",
        description="Tracks per-run model token estimates and projected spend against a configurable budget.",
    ),
    PlatformFeature(
        name="otel-compatible-trace-export",
        category="observability",
        status="implemented",
        description="Exports run events as span-shaped JSON for GenAI observability pipelines.",
    ),
    PlatformFeature(
        name="memory-query-api",
        category="memory",
        status="implemented",
        description="Exposes GraphRAG memory search over HTTP for operators and tools.",
    ),
    PlatformFeature(
        name="sandbox-command-runner",
        category="autonomous dev loop",
        status="implemented",
        description="Provides a timeout-bound subprocess runner for future build execution agents.",
    ),
    PlatformFeature(
        name="mcp-server-mode",
        category="protocols",
        status="seeded",
        description="Publishes an MCP-style manifest for Ruflo run and memory tools.",
    ),
    PlatformFeature(
        name="browser-using-frontend-agent",
        category="autonomous dev loop",
        status="planned",
        description="Use browser automation to visually inspect generated frontends and repair UI issues.",
    ),
    PlatformFeature(
        name="repo-aware-pr-mode",
        category="autonomous dev loop",
        status="planned",
        description="Target an existing repository and produce reviewed pull requests.",
    ),
    PlatformFeature(
        name="spec-driven-contract-mode",
        category="protocols",
        status="planned",
        description="Accept OpenAPI, AsyncAPI, or protobuf specs as first-class swarm goals.",
    ),
    PlatformFeature(
        name="ray-vllm-scaleout",
        category="distributed scale",
        status="planned",
        description="Shard agents over Ray/KubeRay and batch local inference through vLLM or NIM.",
    ),
    PlatformFeature(
        name="human-approval-gates",
        category="operator ux",
        status="planned",
        description="Pause selected DAG nodes for approval, artifact edits, and resume.",
    ),
    PlatformFeature(
        name="slsa-provenance-sbom",
        category="enterprise safety",
        status="planned",
        description="Sign artifacts and emit SBOM/provenance for generated code.",
    ),
)


def list_features() -> list[dict[str, str]]:
    return [asdict(feature) for feature in FEATURES_2026]

