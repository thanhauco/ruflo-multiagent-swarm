const AGENTS = [
  { name: "planner", role: "decompose" },
  { name: "architect", role: "design" },
  { name: "backend", role: "FastAPI" },
  { name: "frontend", role: "React" },
  { name: "database", role: "schema" },
  { name: "reviewer", role: "review" },
  { name: "security", role: "scan" },
  { name: "deployment", role: "Docker / K8s" },
];

const recentRuns = [];
let activeRunId = null;
let activeStream = null;

function $(sel) { return document.querySelector(sel); }

function renderAgents(state = {}) {
  const grid = $("#agentGrid");
  grid.innerHTML = "";
  AGENTS.forEach((a) => {
    const node = document.createElement("div");
    const status = state[a.name] || "idle";
    node.className = `agent ${status}`;
    node.innerHTML = `
      <span class="name">${a.name}</span>
      <span class="role">${a.role}</span>
      <span class="state">${status}</span>
    `;
    grid.appendChild(node);
  });
}

function renderRuns() {
  const list = $("#runs");
  list.innerHTML = "";
  recentRuns.slice().reverse().forEach((run) => {
    const li = document.createElement("li");
    li.className = run.run_id === activeRunId ? "active" : "";
    li.innerHTML = `
      <span class="run-id">${run.run_id}</span>
      <span class="pill">${run.status}</span>
    `;
    li.addEventListener("click", () => attachRun(run.run_id));
    list.appendChild(li);
  });
}

function setStatusBadge(status) {
  const badge = $("#runStatus");
  badge.textContent = status;
  badge.className = "badge";
  if (status === "completed") badge.classList.add("ok");
  else if (status === "failed") badge.classList.add("err");
  else if (status === "running") badge.classList.add("warn");
}

function appendTrace(event) {
  const trace = $("#trace");
  const ts = event.ts ? new Date(event.ts).toLocaleTimeString() : "";
  const name = event.event || "";
  const klass = name.startsWith("run") ? "run" : name.startsWith("task") ? "task" : name.startsWith("memory") ? "memory" : name.startsWith("critic") ? "critic" : "";
  const line = document.createElement("span");
  line.className = "ev";
  const safe = JSON.stringify({ ...event, ts: undefined, event: undefined });
  line.innerHTML = `<span class="ts">${ts}</span>  <span class="name ${klass}">${name}</span>  ${safe}`;
  trace.appendChild(line);
  trace.scrollTop = trace.scrollHeight;
}

function renderArtifacts(artifacts = []) {
  const list = $("#artifacts");
  list.innerHTML = "";
  artifacts.forEach((a) => {
    const li = document.createElement("li");
    const path = encodeURIComponent(a.path).replaceAll("%2F", "/");
    const href = activeRunId ? `/runs/${activeRunId}/artifacts/${path}` : "#";
    li.innerHTML = `
      <a class="path" href="${href}" target="_blank" rel="noreferrer">${a.path}</a>
      <span class="kind ${a.kind || "code"}">${a.kind || "code"}</span>
    `;
    list.appendChild(li);
  });
  $("#runArtifacts").textContent = `${artifacts.length} artifact${artifacts.length === 1 ? "" : "s"}`;
}

function resetRunUI(runId, goal) {
  $("#trace").innerHTML = "";
  $("#runTitle").textContent = `Run ${runId}`;
  $("#runMeta").textContent = goal ? `Goal: ${goal}` : "Streaming events...";
  $("#replay").disabled = !runId;
  renderAgents({});
  renderArtifacts([]);
  setStatusBadge("running");
}

async function fetchRunSnapshot(runId) {
  try {
    const resp = await fetch(`/runs/${runId}`);
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

function applySnapshot(snapshot) {
  if (!snapshot) return;
  if (snapshot.goal) $("#runMeta").textContent = `Goal: ${snapshot.goal}`;
  if (snapshot.metadata?.parent_run_id) {
    $("#runMeta").textContent += ` | replay of ${snapshot.metadata.parent_run_id}`;
  }
  if (snapshot.status) setStatusBadge(snapshot.status);
  if (snapshot.trace?.events) {
    const agentState = {};
    snapshot.trace.events.forEach((ev) => {
      appendTrace(ev);
      if (ev.event === "task.started") agentState[ev.agent] = "running";
      if (ev.event === "task.completed") agentState[ev.agent] = "done";
    });
    renderAgents(agentState);
  }
  if (snapshot.trace?.artifacts) renderArtifacts(snapshot.trace.artifacts);
}

async function attachRun(runId) {
  if (activeStream) {
    activeStream.close();
    activeStream = null;
  }
  activeRunId = runId;
  renderRuns();
  resetRunUI(runId);

  const snapshot = await fetchRunSnapshot(runId);
  applySnapshot(snapshot);
  if (snapshot?.status === "completed" || snapshot?.status === "failed") return;

  const agentState = {};
  const stream = new EventSource(`/runs/${runId}/stream`);
  activeStream = stream;
  stream.onmessage = (msg) => {
    if (!msg.data) return;
    let payload;
    try { payload = JSON.parse(msg.data); } catch { return; }
    if (payload.event === "run.terminal") {
      setStatusBadge(payload.status || "completed");
      stream.close();
      activeStream = null;
      fetchRunSnapshot(runId).then((snap) => {
        if (snap?.trace?.artifacts) renderArtifacts(snap.trace.artifacts);
      });
      const idx = recentRuns.findIndex((r) => r.run_id === runId);
      if (idx >= 0) recentRuns[idx].status = payload.status || "completed";
      renderRuns();
      return;
    }
    appendTrace(payload);
    if (payload.event === "task.started") {
      agentState[payload.agent] = "running";
      renderAgents(agentState);
    }
    if (payload.event === "task.completed") {
      agentState[payload.agent] = "done";
      renderAgents(agentState);
    }
  };
  stream.onerror = () => {
    setStatusBadge("disconnected");
  };
}

async function launchRun() {
  const goal = $("#goal").value.trim();
  if (!goal) {
    $("#launchStatus").textContent = "Enter a goal first.";
    return;
  }
  const button = $("#launch");
  button.disabled = true;
  $("#launchStatus").textContent = "Launching...";
  try {
    const resp = await fetch("/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, wait: $("#waitMode").checked }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    recentRuns.push({ run_id: data.run_id, status: data.status || "running", goal });
    $("#launchStatus").textContent = `Run ${data.run_id} launched`;
    resetRunUI(data.run_id, goal);
    $("#runMeta").textContent = `Goal: ${goal}`;
    activeRunId = data.run_id;
    renderRuns();
    attachRun(data.run_id);
  } catch (err) {
    $("#launchStatus").textContent = `Failed: ${err.message}`;
  } finally {
    button.disabled = false;
  }
}

async function replayRun() {
  if (!activeRunId) return;
  const button = $("#replay");
  button.disabled = true;
  $("#launchStatus").textContent = "Creating replay branch...";
  try {
    const goal = $("#goal").value.trim() || null;
    const resp = await fetch(`/runs/${activeRunId}/replay`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ goal, wait: $("#waitMode").checked }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    recentRuns.push({ run_id: data.run_id, status: data.status || "running", goal: goal || "replay branch" });
    $("#launchStatus").textContent = `Replay ${data.run_id} created`;
    renderRuns();
    attachRun(data.run_id);
  } catch (err) {
    $("#launchStatus").textContent = `Replay failed: ${err.message}`;
  } finally {
    button.disabled = !activeRunId;
  }
}

async function checkHealth() {
  const status = $("#health");
  try {
    const resp = await fetch("/health");
    if (resp.ok) {
      status.classList.add("ok");
      status.querySelector(".label").textContent = "online";
    } else {
      status.classList.add("err");
      status.querySelector(".label").textContent = "degraded";
    }
  } catch {
    status.classList.add("err");
    status.querySelector(".label").textContent = "offline";
  }
}

async function loadFeatures() {
  const list = $("#features");
  try {
    const resp = await fetch("/features");
    const payload = await resp.json();
    list.innerHTML = "";
    payload.features.slice(0, 8).forEach((feature) => {
      const li = document.createElement("li");
      li.innerHTML = `
        <span class="feature-name">${feature.name}</span>
        <span class="feature-status ${feature.status}">${feature.status}</span>
      `;
      li.title = feature.description;
      list.appendChild(li);
    });
  } catch {
    list.innerHTML = `<li><span class="muted">feature registry unavailable</span></li>`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  renderAgents({});
  renderRuns();
  checkHealth();
  loadFeatures();
  $("#launch").addEventListener("click", launchRun);
  $("#replay").addEventListener("click", replayRun);
  $("#goal").addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") launchRun();
  });
});


