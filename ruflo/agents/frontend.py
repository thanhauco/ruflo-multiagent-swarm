"""Frontend code generation agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class FrontendAgent(Agent):
    name = "frontend"
    role = "frontend"

    async def run(self, ctx: RunContext) -> AgentResult:
        await self.complete(ctx, f"Generate React dashboard for {ctx.get('architecture', {})}", purpose="frontend-code")
        app_jsx = dedent(
            '''
            import { useEffect, useState } from "react";
            import "./styles.css";

            const apiBase = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

            export default function App() {
              const [gpus, setGpus] = useState({});
              const [selected, setSelected] = useState("gpu-0");
              const [metrics, setMetrics] = useState([]);

              useEffect(() => {
                fetch(`${apiBase}/api/gpus`).then((r) => r.json()).then(setGpus);
              }, []);

              useEffect(() => {
                fetch(`${apiBase}/api/gpus/${selected}/metrics`)
                  .then((r) => r.json())
                  .then((payload) => setMetrics(payload.samples ?? []));
              }, [selected]);

              const latest = metrics.at(-1) ?? {};

              return (
                <main className="shell">
                  <header className="toolbar">
                    <div>
                      <h1>GPU Telemetry</h1>
                      <p>Cluster utilization, thermals, memory, and power draw.</p>
                    </div>
                    <select value={selected} onChange={(event) => setSelected(event.target.value)}>
                      {Object.values(gpus).map((gpu) => (
                        <option key={gpu.id} value={gpu.id}>{gpu.name}</option>
                      ))}
                    </select>
                  </header>

                  <section className="grid">
                    <Metric label="Utilization" value={`${latest.utilization_pct ?? 0}%`} />
                    <Metric label="Memory" value={`${latest.memory_used_mb ?? 0} MB`} />
                    <Metric label="Temperature" value={`${latest.temperature_c ?? 0} C`} />
                    <Metric label="Power" value={`${latest.power_watts ?? 0} W`} />
                  </section>

                  <table>
                    <thead><tr><th>Timestamp</th><th>Utilization</th><th>Memory</th><th>Temp</th><th>Power</th></tr></thead>
                    <tbody>
                      {metrics.map((row) => (
                        <tr key={row.timestamp}>
                          <td>{new Date(row.timestamp).toLocaleTimeString()}</td>
                          <td>{row.utilization_pct}%</td>
                          <td>{row.memory_used_mb} MB</td>
                          <td>{row.temperature_c} C</td>
                          <td>{row.power_watts} W</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </main>
              );
            }

            function Metric({ label, value }) {
              return <article className="metric"><span>{label}</span><strong>{value}</strong></article>;
            }
            '''
        ).strip() + "\n"
        styles = dedent(
            '''
            :root { font-family: Inter, system-ui, sans-serif; color: #172026; background: #f6f8fa; }
            body { margin: 0; }
            .shell { max-width: 1180px; margin: 0 auto; padding: 32px; }
            .toolbar { display: flex; justify-content: space-between; align-items: end; gap: 16px; margin-bottom: 24px; }
            h1 { margin: 0; font-size: 32px; }
            p { margin: 6px 0 0; color: #5a6672; }
            select { min-width: 220px; padding: 10px 12px; border: 1px solid #ccd4dd; border-radius: 6px; background: white; }
            .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 24px; }
            .metric { background: white; border: 1px solid #dde4eb; border-radius: 8px; padding: 18px; }
            .metric span { display: block; color: #637083; font-size: 13px; margin-bottom: 8px; }
            .metric strong { font-size: 26px; }
            table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #dde4eb; }
            th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #e8edf2; }
            th { background: #eef3f7; color: #2a3440; font-size: 13px; }
            @media (max-width: 780px) { .toolbar { align-items: stretch; flex-direction: column; } .grid { grid-template-columns: repeat(2, 1fr); } }
            '''
        ).strip() + "\n"
        package_json = dedent(
            '''
            {
              "scripts": { "dev": "vite", "build": "vite build", "preview": "vite preview" },
              "dependencies": { "@vitejs/plugin-react": "latest", "vite": "latest", "react": "latest", "react-dom": "latest" },
              "devDependencies": {}
            }
            '''
        ).strip() + "\n"
        main_jsx = 'import React from "react";\nimport { createRoot } from "react-dom/client";\nimport App from "./App.jsx";\n\ncreateRoot(document.getElementById("root")).render(<App />);\n'
        index_html = '<div id="root"></div><script type="module" src="/src/main.jsx"></script>\n'
        ctx.add_artifact("app/frontend/package.json", package_json, producer=self.name, kind="config")
        ctx.add_artifact("app/frontend/index.html", index_html, producer=self.name)
        ctx.add_artifact("app/frontend/src/main.jsx", main_jsx, producer=self.name)
        ctx.add_artifact("app/frontend/src/App.jsx", app_jsx, producer=self.name)
        ctx.add_artifact("app/frontend/src/styles.css", styles, producer=self.name)
        ctx.set("frontend_files", ["app/frontend/src/App.jsx", "app/frontend/src/styles.css"])
        return AgentResult(agent=self.name, summary="Generated React dashboard.")
