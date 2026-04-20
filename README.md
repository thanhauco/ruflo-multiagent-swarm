# Ruflo Multi-Agent SDLC Swarm

A **Distributed Multi-LLM Agentic SDLC Platform** inspired by [Ruflo](https://github.com/ruvnet/ruflo).

Give it a one-line product idea, and a swarm of specialized AI agents will plan,
design, build, review, secure, and ship it through a Ruflo-style orchestrator
with GraphRAG memory, multi-provider LLM routing, GPU-aware scheduling, live SSE
streaming, and an operator console.

## Example

```bash
ruflo run "Build a scalable GPU telemetry dashboard with FastAPI + React."
```

Pipeline executed automatically:

| # | Agent       | Role                                          |
|---|-------------|-----------------------------------------------|
| 1 | Planner     | Decomposes the task into a DAG of subtasks    |
| 2 | Architect   | Designs services, contracts, data flow        |
| 3 | Backend     | Generates FastAPI services & routes           |
| 4 | Frontend    | Generates React UI                            |
| 5 | DB          | Designs schema + migrations                   |
| 6 | Reviewer    | Static review + refactor suggestions          |
| 7 | Security    | OWASP / dependency / secret scan              |
| 8 | Deployment  | Dockerfiles, Compose, K8s manifests, Helm     |
| * | Memory      | Stores successful patterns into GraphRAG      |

## Architecture

```text
                +------------------------------+
   user ---->   |      Ruflo Orchestrator      |
                |  DAG executor + LLM router   |
                +-------------+----------------+
                              |
       +----------------------+----------------------+
       v                      v                      v
 +------------+        +-------------+        +--------------+
 | LLM Router |        | GPU Scheduler|        |GraphRAG Memory|
 | multi-LLM  |        | NVML/mock    |        | JSON today    |
 +------------+        +-------------+        +--------------+
       |                      |                      |
       +----------> Specialized Agents <------------+
        Planner | Architect | Backend | Frontend
        DB | Reviewer | Security | Deployment
```

## Quick Start

```bash
pip install -e .
ruflo run "Build a GPU telemetry dashboard with FastAPI + React"

# or run the API and operator UI
uvicorn ruflo.api:app --reload
```

Open `http://localhost:8000/` for the Ruflo Swarm Console. Outputs are written
to `./out/<run_id>/`.

## API Surface

| Route | Purpose |
|---|---|
| `GET /` | Operator console UI |
| `GET /health` | Health probe |
| `POST /runs` | Launch a swarm run |
| `GET /runs/{run_id}` | Read run status, trace, and artifacts metadata |
| `GET /runs/{run_id}/stream` | Server-sent event stream for live runs |
| `GET /runs/{run_id}/spans` | Span-shaped trace export for observability tools |
| `GET /runs/{run_id}/artifacts/{path}` | Download generated artifacts safely |
| `GET /features` | 2026 feature registry and implementation status |
| `GET /memory/search?q=...` | Search GraphRAG memory |
| `GET /mcp/manifest` | MCP-style tool manifest |

## 2026 Advanced Feature Plan

Ruflo now tracks advanced platform work as a first-class feature registry. The
current implementation lands the foundation first, then leaves clear extension
points for heavier distributed and enterprise capabilities.

| Feature | Status | Notes |
|---|---:|---|
| Critic/verifier loop | Implemented | Emits `critic.verdict` after every agent result. |
| Cost budget ledger | Implemented | Emits `budget.update` events with token and estimated spend totals. |
| OTel-compatible trace export | Implemented | Writes `trace.otlp.json` and serves spans through `/runs/{id}/spans`. |
| Memory query API | Implemented | GraphRAG search is available at `/memory/search`. |
| Sandbox command runner | Implemented | Timeout-bound subprocess runner ready for build execution agents. |
| MCP server mode | Seeded | `/mcp/manifest` exposes Ruflo tools for MCP integration. |
| Reasoning replay and branching | Implemented | Replay prior runs through `/runs/{id}/replay` with lineage metadata. |
| Browser-using frontend agent | Planned | Use browser automation to visually inspect generated UIs and self-repair. |
| Repo-aware PR mode | Planned | Target an existing repo and produce reviewed pull requests. |
| Spec-driven contract mode | Planned | Accept OpenAPI, AsyncAPI, or protobuf specs as swarm goals. |
| Ray/vLLM scale-out | Planned | Use Ray/KubeRay plus vLLM/NIM for distributed local inference. |
| Human approval gates | Planned | Pause selected nodes for review, edits, and resume. |
| SLSA provenance and SBOM | Planned | Sign artifacts and emit software supply-chain evidence. |

## Configuration

Copy `.env.example` to `.env` and fill in any of:

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
GROQ_API_KEY=...
OLLAMA_BASE_URL=http://localhost:11434
NEO4J_URI=bolt://localhost:7687
RUFLO_BUDGET_USD=1.00
RUFLO_USD_PER_1K_TOKENS=0.003
```

If no provider keys are set, the system falls back to a deterministic `MockLLM`
so the full pipeline still runs end-to-end.

## Layout

```text
ruflo/
  agents/          # 9 specialized agents
  core/            # Orchestrator, DAG, run context
  distributed/     # Async worker pool
  governance/      # Feature registry, critic, budget ledger
  llm/             # Multi-LLM router + providers
  memory/          # GraphRAG knowledge graph
  observability/   # Trace/span export helpers
  runtime/         # Sandbox runner foundations
  scheduler/       # GPU-aware task scheduler
  webui/           # Operator console
  cli.py
  api.py
  mcp.py
deploy/            # Docker + K8s manifests for the platform itself
```



