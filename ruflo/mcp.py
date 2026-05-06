"""MCP-style tool manifest for Ruflo integrations."""
from __future__ import annotations


def tool_manifest() -> dict:
    return {
        "server": "ruflo-multiagent-swarm",
        "version": "0.1.0",
        "tools": [
            {
                "name": "ruflo.create_run",
                "description": "Launch a multi-agent SDLC swarm run from a product goal.",
                "input_schema": {"type": "object", "properties": {"goal": {"type": "string"}}, "required": ["goal"]},
            },
            {
                "name": "ruflo.get_run",
                "description": "Read live status, trace, and artifacts for a swarm run.",
                "input_schema": {"type": "object", "properties": {"run_id": {"type": "string"}}, "required": ["run_id"]},
            },
            {
                "name": "ruflo.search_memory",
                "description": "Search Ruflo GraphRAG memory for prior run knowledge.",
                "input_schema": {"type": "object", "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["q"]},
            },
        ],
    }
