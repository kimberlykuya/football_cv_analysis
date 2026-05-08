"""GPU monitoring and telemetry."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from collections import deque
from typing import Optional

try:
    import torch
except ImportError:
    torch = None  # type: ignore


@dataclass
class GPUStatus:
    """GPU status snapshot."""

    gpu_util_pct: float
    vram_used_mb: float
    vram_total_mb: float
    temperature_c: Optional[float]
    device_name: str
    cuda_available: bool
    timestamp: float


class GPUMonitor:
    """Background GPU monitoring with ring buffer history."""

    def __init__(self, sample_interval_sec: float = 2.0, history_size: int = 300):
        self.sample_interval_sec = sample_interval_sec
        self.history_size = history_size
        self.history: deque[GPUStatus] = deque(maxlen=history_size)
        self._sampling_thread: Optional[threading.Thread] = None
        self._running = False

    def start(self) -> None:
        """Start background sampling thread."""
        if self._running:
            return

        self._running = True
        self._sampling_thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._sampling_thread.start()

    def stop(self) -> None:
        """Stop background sampling thread."""
        self._running = False
        if self._sampling_thread:
            self._sampling_thread.join(timeout=5)

    def _sample_loop(self) -> None:
        """Background sampling loop."""
        while self._running:
            try:
                status = self.get_status()
                self.history.append(status)
            except Exception:
                pass
            time.sleep(self.sample_interval_sec)

    def get_status(self) -> GPUStatus:
        """Get current GPU status."""
        cuda_available = torch.cuda.is_available() if torch else False

        if not cuda_available:
            return GPUStatus(
                gpu_util_pct=0.0,
                vram_used_mb=0.0,
                vram_total_mb=0.0,
                temperature_c=None,
                device_name="CPU (no CUDA)",
                cuda_available=False,
                timestamp=time.time(),
            )

        try:
            # Try AMD ROCm first
            return self._get_amd_status()
        except Exception:
            pass

        try:
            # Fall back to NVIDIA
            return self._get_nvidia_status()
        except Exception:
            pass

        try:
            # Fall back to torch.cuda basic stats
            return self._get_torch_status()
        except Exception:
            pass

        return GPUStatus(
            gpu_util_pct=0.0,
            vram_used_mb=0.0,
            vram_total_mb=0.0,
            temperature_c=None,
            device_name="GPU (unavailable)",
            cuda_available=False,
            timestamp=time.time(),
        )

    def _get_amd_status(self) -> GPUStatus:
        """Get AMD ROCm GPU status."""
        try:
            import amdsmi
        except ImportError:
            raise RuntimeError("amdsmi not available")

        devices = amdsmi.amd_get_gpu_device_handles()
        if not devices:
            raise RuntimeError("No AMD GPUs found")

        device = devices[0]

        # GPU utilization
        gpu_util = amdsmi.amd_get_gpu_load_percent(device)

        # VRAM usage
        mem_info = amdsmi.amd_get_gpu_memory_usage(device)
        vram_used_mb = mem_info.get("vram_used", 0) / 1024 / 1024
        vram_total_mb = mem_info.get("vram_total", 0) / 1024 / 1024

        # Temperature (may not be available)
        temp_c = None
        try:
            temp_c = amdsmi.amd_get_gpu_temp(device, sensor=0)
        except Exception:
            pass

        device_name = f"AMD GPU {device}"

        return GPUStatus(
            gpu_util_pct=float(gpu_util),
            vram_used_mb=vram_used_mb,
            vram_total_mb=vram_total_mb,
            temperature_c=temp_c,
            device_name=device_name,
            cuda_available=True,
            timestamp=time.time(),
        )

    def _get_nvidia_status(self) -> GPUStatus:
        """Get NVIDIA GPU status via pynvml."""
        try:
            import pynvml
        except ImportError:
            raise RuntimeError("pynvml not available")

        pynvml.nvmlInit()
        device = pynvml.nvmlDeviceGetHandleByIndex(0)

        # GPU utilization
        util = pynvml.nvmlDeviceGetUtilizationRates(device)
        gpu_util = util.gpu

        # VRAM usage
        mem_info = pynvml.nvmlDeviceGetMemoryInfo(device)
        vram_used_mb = mem_info.used / 1024 / 1024
        vram_total_mb = mem_info.total / 1024 / 1024

        # Temperature
        try:
            temp_c = pynvml.nvmlDeviceGetTemperature(device, 0)
        except Exception:
            temp_c = None

        # Device name
        device_name = pynvml.nvmlDeviceGetName(device).decode("utf-8")

        pynvml.nvmlShutdown()

        return GPUStatus(
            gpu_util_pct=float(gpu_util),
            vram_used_mb=vram_used_mb,
            vram_total_mb=vram_total_mb,
            temperature_c=float(temp_c) if temp_c else None,
            device_name=device_name,
            cuda_available=True,
            timestamp=time.time(),
        )

    def _get_torch_status(self) -> GPUStatus:
        """Get basic GPU status from torch.cuda."""
        if not torch or not torch.cuda.is_available():
            raise RuntimeError("torch.cuda not available")

        gpu_util = 0.0  # torch.cuda doesn't expose utilization directly
        vram_used_mb = torch.cuda.memory_allocated() / 1024 / 1024
        vram_total_mb = torch.cuda.get_device_properties(0).total_memory / 1024 / 1024

        device_name = torch.cuda.get_device_name(0)

        return GPUStatus(
            gpu_util_pct=gpu_util,
            vram_used_mb=vram_used_mb,
            vram_total_mb=vram_total_mb,
            temperature_c=None,
            device_name=device_name,
            cuda_available=True,
            timestamp=time.time(),
        )

    def get_history(self, limit: int = 300) -> list[dict]:
        """Get recent sampling history."""
        return [
            {
                "timestamp": s.timestamp,
                "gpu_util_pct": s.gpu_util_pct,
                "vram_used_mb": s.vram_used_mb,
                "vram_total_mb": s.vram_total_mb,
                "temperature_c": s.temperature_c,
            }
            for s in list(self.history)[-limit:]
        ]


# Global monitor instance
_global_monitor: Optional[GPUMonitor] = None


def get_monitor() -> GPUMonitor:
    """Get or create global GPU monitor."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = GPUMonitor()
        _global_monitor.start()
    return _global_monitor
