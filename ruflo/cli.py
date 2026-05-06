"""CLI entrypoint for Ruflo swarm."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from ruflo.core.orchestrator import Orchestrator

app = typer.Typer(help="Ruflo multi-agent SDLC swarm")
console = Console()


@app.command()
def run(goal: str) -> None:
    """Run the SDLC swarm for a product goal."""
    result = asyncio.run(Orchestrator().run(goal))
    table = Table(title="Ruflo Run Completed")
    table.add_column("Run ID")
    table.add_column("Artifacts")
    table.add_column("Trace")
    table.add_row(result.run_id, str(result.artifacts), result.trace_path)
    console.print(table)


@app.command("trace")
def trace_cmd(run_id: str, out_dir: str = typer.Option("./out", help="Base output folder")) -> None:
    """Print trace events for a previous run."""
    trace_file = Path(out_dir) / run_id / "trace.json"
    if not trace_file.exists():
        raise typer.BadParameter(f"Trace not found: {trace_file}")
    payload = json.loads(trace_file.read_text(encoding="utf-8"))
    for event in payload.get("events", []):
        console.print(f"[{event.get('ts')}] {event.get('event')} -> {event}")


if __name__ == "__main__":
    app()
