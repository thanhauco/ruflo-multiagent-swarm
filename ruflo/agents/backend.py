"""Backend code generation agent."""
from __future__ import annotations

from textwrap import dedent

from ruflo.agents.base import Agent, AgentResult
from ruflo.core.context import RunContext


class BackendAgent(Agent):
    name = "backend"
    role = "backend"

    async def run(self, ctx: RunContext) -> AgentResult:
        architecture = ctx.get("architecture", {})
        await self.complete(ctx, f"Generate FastAPI backend for {architecture}", purpose="backend-code")
        main_py = dedent(
            '''
            from fastapi import FastAPI, HTTPException
            from fastapi.middleware.cors import CORSMiddleware

            from telemetry import GPU_DEVICES, metric_history

            app = FastAPI(title="GPU Telemetry API", version="0.1.0")
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["http://localhost:5173", "http://localhost:3000"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )


            @app.get("/health")
            def health():
                return {"status": "ok"}


            @app.get("/api/gpus")
            def list_gpus():
                return GPU_DEVICES


            @app.get("/api/gpus/{gpu_id}/metrics")
            def gpu_metrics(gpu_id: str):
                if gpu_id not in GPU_DEVICES:
                    raise HTTPException(status_code=404, detail="GPU not found")
                return {"gpu_id": gpu_id, "samples": metric_history(gpu_id)}
            '''
        ).strip() + "\n"
        telemetry_py = dedent(
            '''
            from datetime import datetime, timedelta, timezone
            from random import Random

            random = Random(42)

            GPU_DEVICES = {
                "gpu-0": {"id": "gpu-0", "name": "NVIDIA A100", "memory_total_mb": 40960, "status": "healthy"},
                "gpu-1": {"id": "gpu-1", "name": "NVIDIA L40S", "memory_total_mb": 46080, "status": "healthy"},
            }


            def metric_history(gpu_id: str, points: int = 24):
                now = datetime.now(timezone.utc)
                rows = []
                for offset in range(points):
                    ts = now - timedelta(minutes=(points - offset) * 5)
                    rows.append(
                        {
                            "timestamp": ts.isoformat(),
                            "utilization_pct": 45 + random.randint(-12, 35),
                            "memory_used_mb": 12000 + random.randint(-2500, 9000),
                            "temperature_c": 62 + random.randint(-8, 11),
                            "power_watts": 210 + random.randint(-35, 70),
                        }
                    )
                return rows
            '''
        ).strip() + "\n"
        ctx.add_artifact("app/backend/main.py", main_py, producer=self.name)
        ctx.add_artifact("app/backend/telemetry.py", telemetry_py, producer=self.name)
        ctx.add_artifact("app/backend/requirements.txt", "fastapi\nuvicorn[standard]\n", producer=self.name, kind="config")
        ctx.set("backend_files", ["app/backend/main.py", "app/backend/telemetry.py"])
        return AgentResult(agent=self.name, summary="Generated FastAPI backend.")
