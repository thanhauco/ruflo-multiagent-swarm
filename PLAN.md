# Master Plan — Ruflo Multi-Agent SDLC Swarm

> A distributed, multi-LLM agentic platform that turns a one-line product idea
> into a fully scaffolded, tested, reviewed, secured and deployable codebase —
> coordinated through a Ruflo-style orchestrator with GraphRAG memory and
> GPU-aware scheduling.

---

## 0. North Star

**Input:** `"Build a scalable GPU telemetry dashboard with FastAPI + React."`
**Output:** A directory of production-shaped artifacts (services, UI, schema,
review report, security report, Docker + K8s manifests) plus a replayable trace and a
GraphRAG memory entry capturing what worked.

Success = pipeline runs end-to-end with **zero LLM keys** (mock provider) and
also runs against **real providers** (OpenAI / Anthropic / Azure OpenAI / Groq /
Ollama) without code changes.

---

## 1. Guiding Principles

1. **Orchestrator-first** — every agent is a pure function over `RunContext`.
   Coordination logic lives in the orchestrator, not in agents.
2. **Provider-agnostic** — agents call `LLMRouter.complete(role=...)`, never a
   specific SDK. Routing decisions are policy, not code.
3. **Deterministic fallback** — `MockLLM` keeps the demo green in CI / offline.
4. **Replayable** — every run emits `trace.json` + artifacts on disk.
5. **Composable distribution** — start with `asyncio` worker pool; opt into
   Ray with one env var (`RUFLO_USE_RAY=1`).
6. **Memory compounds** — successful runs are distilled into GraphRAG nodes
   (patterns, decisions, anti-patterns) reused on future runs.

---

## 2. Milestone Phases

### Phase 1 — Skeleton & Contracts  *(foundation)*
- Project scaffold (`pyproject.toml`, `.env.example`, package layout).
- `RunContext`, `Artifact`, `TaskGraph`, `Agent` base class.
- Stub `Orchestrator.run()` that walks a hard-coded DAG.
- `MockLLM` provider so the loop is runnable with zero config.

**Exit criteria:** `python -m ruflo.cli run "hello"` produces a `run_dir/` with
a trace and at least one artifact.

---

### Phase 2 — Multi-LLM Router
- Provider adapters: `OpenAIProvider`, `AnthropicProvider`,
  `AzureOpenAIProvider`, `GroqProvider`, `OllamaProvider`, `MockProvider`.
- `LLMRouter` with role-based policy
  (`planner → strong-reasoner`, `frontend → fast-coder`, etc.).
- Cost / latency / capability metadata per provider.
- Automatic failover + retry with backoff.

**Exit criteria:** swapping `OPENAI_API_KEY` in `.env` changes the provider
used by the planner — without touching any agent.

---

### Phase 3 — Specialized Agents (the SDLC swarm)
Implement the 9 agents, each as `Agent.run(ctx) -> None`:

| Phase | Agent       | Input from blackboard      | Output to blackboard           | Artifacts                         |
|-------|-------------|----------------------------|--------------------------------|-----------------------------------|
| 3.1   | Planner     | `goal`                     | `plan` (subtasks, DAG hints)   | `PLAN.md`                         |
| 3.2   | Architect   | `plan`                     | `architecture` (services, IO)  | `ARCHITECTURE.md`, `diagram.mmd`  |
| 3.3   | Backend     | `architecture`             | `backend_files`                | `app/backend/**`                  |
| 3.4   | Frontend    | `architecture`             | `frontend_files`               | `app/frontend/**`                 |
| 3.5   | DB          | `architecture`             | `schema`                       | `db/schema.sql`, `migrations/**`  |
| 3.7   | Reviewer    | all code artifacts         | `review_report`                | `REVIEW.md`                       |
| 3.8   | Security    | all code artifacts         | `security_report`              | `SECURITY.md`                     |
| 3.9   | Deployment  | all artifacts              | `deploy_plan`                  | `Dockerfile`, `compose.yaml`, `k8s/**` |

**Exit criteria:** end-to-end run against `MockLLM` produces a coherent
mini-project on disk.

---

### Phase 4 — GraphRAG Memory
- `KnowledgeGraph` abstraction (Neo4j adapter + JSON file fallback).
- Node types: `Pattern`, `Decision`, `AntiPattern`, `Component`, `Run`.
- Edges: `USES`, `REPLACES`, `CONFLICTS_WITH`, `DERIVED_FROM`.
- Hooks:
  - **read** at planner/architect time (retrieve relevant patterns).
  - **write** after a successful run (extract reusable patterns).
- Simple embedding-free retrieval first (tag + keyword), pluggable later.

**Exit criteria:** second run on a similar goal pulls in stored patterns and
the trace shows `memory.hit` events.

---

### Phase 5 — GPU-aware Scheduler & Distributed Execution
- `GpuScheduler`:
  - Probes GPUs via `pynvml` if available, else a `MockGpuPool`.
  - Tracks per-GPU free memory + utilization.
  - Allocates "GPU units" to tasks declaring `weight_gpu > 0`.
- `WorkerPool`:
  - Default: bounded `asyncio` semaphore.
  - Optional: Ray actors when `RUFLO_USE_RAY=1`.
- Orchestrator picks ready DAG nodes and submits them respecting both CPU
  concurrency and GPU budget.

**Exit criteria:** scheduler logs show parallel agent execution and GPU
allocation events; toggling `RUFLO_USE_RAY=1` runs the same DAG on Ray.

---

### Phase 6 — Surfaces (CLI + API + Deploy)
- `ruflo run "<goal>"` — Typer CLI with rich progress UI.
- `ruflo trace <run_id>` — pretty-print a previous run.
- `ruflo.api:app` — FastAPI server exposing:
  - `POST /runs` → start a run (returns `run_id`).
  - `GET  /runs/{id}` → status + artifacts.
  - `GET  /runs/{id}/stream` → server-sent events of the trace.
- `deploy/Dockerfile`, `deploy/compose.yaml`, `deploy/k8s/*.yaml` for the
  platform itself.

**Exit criteria:** `docker compose up` boots the API; a `POST /runs` produces a
streaming trace and final artifact bundle.

---

### Phase 7 — Quality & Docs
- Static checks: imports, package metadata, and README quick-start consistency.
- Smoke validation: full mock run can produce an artifact bundle on demand.
- `ARCHITECTURE.md` (this milestone’s sibling doc) kept in sync.
- README quick-start verified on a clean machine.

**Exit criteria:** README copy-paste works and generated artifacts compile in their target runtimes.

---

## 3. Out-of-Scope (v0.1)

- Real fine-tuning / training loops.
- Long-running stateful agents (everything is single-shot per DAG node).
- Multi-tenant auth on the API (single-user dev surface).
- Streaming token UIs in the React preview (artifacts only).

These are explicit non-goals to keep v0.1 shippable. They are good v0.2
candidates (especially streaming + auth).

---

## 4. Risks & Mitigations

| Risk                                         | Mitigation                                          |
|----------------------------------------------|-----------------------------------------------------|
| Provider API drift / outages                 | Adapter pattern + `MockLLM` fallback + retries.     |
| GPU not present on dev machines              | `MockGpuPool` with configurable inventory.          |
| Agent outputs are unstructured / unparseable | All agents return JSON-schema-validated payloads.   |
| Memory grows unbounded                       | TTL + max-node cap on JSON adapter; Cypher LIMITs.  |
| Ray dependency heaviness                     | Optional extra (`pip install .[ray]`); off by default. |

---

## 5. Phase → Deliverable map

| Phase | Code modules added                                    |
|-------|-------------------------------------------------------|
| 1     | `core/`, `cli.py`, `llm/mock.py`                      |
| 2     | `llm/router.py`, `llm/providers/*`                    |
| 3     | `agents/*` (planner → deployment)                     |
| 4     | `memory/graph.py`, `memory/adapters/*`                |
| 5     | `scheduler/gpu.py`, `distributed/pool.py`             |
| 6     | `api.py`, `deploy/**`                                 |
| 7     | polished `README.md`, `ARCHITECTURE.md`               |

