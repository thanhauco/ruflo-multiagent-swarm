"""Async worker pool used by the orchestrator."""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class WorkerPool:
    def __init__(self, concurrency: int = 4) -> None:
        self.semaphore = asyncio.Semaphore(concurrency)

    async def submit(self, fn: Callable[[], Awaitable[T]]) -> T:
        async with self.semaphore:
            return await fn()
