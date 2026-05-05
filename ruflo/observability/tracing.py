"""Span-shaped trace export for Ruflo event streams."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def events_to_spans(run_id: str, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        name = event.get("event", "event")
        spans.append(
            {
                "trace_id": run_id,
                "span_id": f"{index:016x}",
                "parent_span_id": None,
                "name": name,
                "kind": "internal",
                "start_time": event.get("ts", _timestamp()),
                "end_time": event.get("ts", _timestamp()),
                "attributes": {k: v for k, v in event.items() if k not in {"ts", "event"}},
            }
        )
    return spans
