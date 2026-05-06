"""FastAPI surface for managing swarm runs."""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ruflo.core.orchestrator import Orchestrator
from ruflo.governance.features import list_features
from ruflo.mcp import tool_manifest
from ruflo.observability.tracing import events_to_spans

app = FastAPI(title="Ruflo Swarm API", version="0.1.0")
_orchestrator = Orchestrator()

_WEBUI_DIR = Path(__file__).parent / "webui"
if _WEBUI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=_WEBUI_DIR), name="ui")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(_WEBUI_DIR / "index.html")


@dataclass
class RunState:
    run_id: str
    goal: str
    status: str
    queue: asyncio.Queue[dict[str, Any]]
    task: asyncio.Task[Any] | None = None
    artifacts: int = 0
    trace_path: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


_runs: dict[str, RunState] = {}


class RunRequest(BaseModel):
    goal: str
    wait: bool = False
    metadata: dict[str, Any] | None = None


class ReplayRequest(BaseModel):
    goal: str | None = None
    from_event: int | None = None
    wait: bool = False


def _load_trace(run_id: str) -> dict[str, Any] | None:
    state = _runs.get(run_id)
    if state and state.trace_path and Path(state.trace_path).exists():
        return json.loads(Path(state.trace_path).read_text(encoding="utf-8"))

    trace = Path("./out") / run_id / "trace.json"
    if trace.exists():
        return json.loads(trace.read_text(encoding="utf-8"))
    return None


def _run_dir(run_id: str) -> Path:
    state = _runs.get(run_id)
    if state and state.trace_path:
        return Path(state.trace_path).parent
    return Path("./out") / run_id


async def _execute_run(state: RunState) -> None:
    try:
        state.status = "running"

        def _emit(event: dict[str, Any]) -> None:
            state.queue.put_nowait(event)

        result = await _orchestrator.run(
            state.goal,
            run_id=state.run_id,
            event_hook=_emit,
            metadata=state.metadata,
        )
        state.artifacts = result.artifacts
        state.trace_path = result.trace_path
        state.status = "completed"
    except Exception as exc:
        state.status = "failed"
        state.error = str(exc)
    finally:
        state.queue.put_nowait({"event": "run.terminal", "status": state.status, "error": state.error})


async def _launch_run(goal: str, *, wait: bool = False, metadata: dict[str, Any] | None = None) -> RunState:
    run_id = uuid.uuid4().hex[:12]
    state = RunState(
        run_id=run_id,
        goal=goal,
        status="queued",
        queue=asyncio.Queue(),
        metadata=metadata or {},
    )
    _runs[run_id] = state
    if wait:
        await _execute_run(state)
    else:
        state.task = asyncio.create_task(_execute_run(state))
    return state


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/features")
def features() -> dict[str, list[dict[str, str]]]:
    return {"features": list_features()}


@app.get("/mcp/manifest")
def mcp_manifest() -> dict:
    return tool_manifest()


@app.get("/memory/search")
def search_memory(q: str, limit: int = 5) -> dict[str, Any]:
    hits = _orchestrator.memory.search(q, limit=limit)
    return {
        "query": q,
        "results": [
            {
                "kind": hit.kind,
                "title": hit.title,
                "body": hit.body,
                "tags": hit.tags,
                "metadata": hit.metadata,
            }
            for hit in hits
        ],
    }


@app.post("/runs")
async def create_run(req: RunRequest) -> dict[str, str | int]:
    state = await _launch_run(req.goal, wait=req.wait, metadata=req.metadata)
    return {"run_id": state.run_id, "status": state.status}


@app.post("/runs/{run_id}/replay")
async def replay_run(run_id: str, req: ReplayRequest) -> dict[str, str | int]:
    trace = _load_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="source run not found")

    events = trace.get("events", [])
    event_index = req.from_event if req.from_event is not None else len(events) - 1
    if event_index < 0 or event_index >= len(events):
        raise HTTPException(status_code=400, detail="from_event is outside the source trace")

    goal = req.goal or trace.get("goal")
    if not goal:
        raise HTTPException(status_code=400, detail="source run does not include a goal")

    metadata = {
        "parent_run_id": run_id,
        "branch_from_event": event_index,
        "branch_from_event_name": events[event_index].get("event"),
        "mode": "replay-branch",
    }
    state = await _launch_run(goal, wait=req.wait, metadata=metadata)
    return {
        "run_id": state.run_id,
        "status": state.status,
        "parent_run_id": run_id,
        "branch_from_event": event_index,
    }


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    state = _runs.get(run_id)
    if not state:
        payload = _load_trace(run_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="run not found")
        payload["status"] = "completed"
        return payload

    response: dict[str, Any] = {
        "run_id": run_id,
        "goal": state.goal,
        "status": state.status,
        "artifacts": state.artifacts,
        "trace_path": state.trace_path,
        "error": state.error,
        "metadata": state.metadata,
    }
    payload = _load_trace(run_id)
    if payload is not None:
        response["trace"] = payload
    return response


@app.get("/runs/{run_id}/spans")
def get_run_spans(run_id: str) -> dict[str, Any]:
    trace = _load_trace(run_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="run not found")

    spans_file = _run_dir(run_id) / "trace.otlp.json"
    if spans_file.exists():
        return {"run_id": run_id, "spans": json.loads(spans_file.read_text(encoding="utf-8"))}
    return {"run_id": run_id, "spans": events_to_spans(run_id, trace.get("events", []))}


@app.get("/runs/{run_id}/artifacts/{artifact_path:path}")
def get_artifact(run_id: str, artifact_path: str) -> FileResponse:
    run_dir = _run_dir(run_id).resolve()
    target = (run_dir / artifact_path).resolve()
    if run_dir not in target.parents and target != run_dir:
        raise HTTPException(status_code=400, detail="invalid artifact path")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(target)


@app.get("/runs/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    state = _runs.get(run_id)
    if not state:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_stream() -> Any:
        while True:
            try:
                event = await asyncio.wait_for(state.queue.get(), timeout=1.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield "event: ping\ndata: {}\n\n"

            if state.status in {"completed", "failed"} and state.queue.empty():
                break

    return StreamingResponse(event_stream(), media_type="text/event-stream")
