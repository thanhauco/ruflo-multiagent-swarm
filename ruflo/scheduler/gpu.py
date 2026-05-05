"""GPU-aware scheduling primitives."""
from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class GpuDevice:
    index: int
    memory_total_mb: int
    memory_free_mb: int
    utilization_pct: int


@dataclass
class ResourceLease:
    task: str
    gpu_index: int | None = None
    gpu_units: float = 0.0


class GpuScheduler:
    """Small scheduler that uses NVML when present and mock GPUs otherwise."""

    def __init__(self) -> None:
        self.devices = self._probe_devices()

    def _probe_devices(self) -> list[GpuDevice]:
        try:
            import pynvml  # type: ignore

            pynvml.nvmlInit()
            devices: list[GpuDevice] = []
            for index in range(pynvml.nvmlDeviceGetCount()):
                handle = pynvml.nvmlDeviceGetHandleByIndex(index)
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                devices.append(
                    GpuDevice(
                        index=index,
                        memory_total_mb=int(mem.total / 1024 / 1024),
                        memory_free_mb=int(mem.free / 1024 / 1024),
                        utilization_pct=int(util.gpu),
                    )
                )
            return devices
        except Exception:
            return [GpuDevice(index=0, memory_total_mb=24576, memory_free_mb=24576, utilization_pct=0)]

    def pick_gpu(self) -> GpuDevice | None:
        if not self.devices:
            return None
        return max(self.devices, key=lambda d: (d.memory_free_mb, -d.utilization_pct))

    @asynccontextmanager
    async def lease(self, task: str, gpu_units: float = 0.0) -> AsyncIterator[ResourceLease]:
        gpu = self.pick_gpu() if gpu_units > 0 else None
        lease = ResourceLease(task=task, gpu_index=gpu.index if gpu else None, gpu_units=gpu_units)
        yield lease
