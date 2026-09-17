"""Local, best-effort hardware discovery for SIMORGH.

The probe is deliberately read-only. It never uploads telemetry and does not
require a GPU-specific Python package. Unknown values stay unknown instead of
being guessed.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class HardwareProfile:
    architecture: str
    os_name: str
    kernel: str
    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    cpu_mhz: float | None
    ram_gb: float
    disk_free_gb: float
    gpu: str | None
    gpu_vram_gb: float | None
    tier: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _read_first(paths: tuple[str, ...]) -> str:
    for raw in paths:
        try:
            value = Path(raw).read_text(encoding="utf-8", errors="ignore").strip()
        except OSError:
            continue
        if value:
            return value
    return ""


def _cpu_model() -> str:
    model = platform.processor().strip()
    if model:
        return model
    line = _read_first(("/proc/cpuinfo",))
    match = re.search(r"^model name\s*:\s*(.+)$", line, re.MULTILINE)
    return match.group(1).strip() if match else "unknown"


def _cpu_mhz() -> float | None:
    try:
        text = Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    match = re.search(r"^cpu MHz\s*:\s*([0-9.]+)$", text, re.MULTILINE)
    return float(match.group(1)) if match else None


def _ram_gb() -> float:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return round((pages * page_size) / (1024**3), 2)
    except (OSError, ValueError, AttributeError):
        return 0.0


def _gpu_info() -> tuple[str | None, float | None]:
    try:
        result = subprocess.run(
            ["lspci", "-nn"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None, None
    names: list[str] = []
    for line in result.stdout.splitlines():
        if re.search(r"vga compatible controller|3d controller|display controller", line, re.I):
            names.append(line.split(": ", 1)[-1].strip())
    if not names:
        return None, None
    return "; ".join(names), None


def classify(ram_gb: float, cpu_threads: int, gpu_vram_gb: float | None) -> str:
    """Conservative model tier, based on resources available to the process."""
    if gpu_vram_gb is not None and gpu_vram_gb >= 8 and ram_gb >= 16:
        return "large"
    if ram_gb >= 16 or (ram_gb >= 8 and cpu_threads >= 8):
        return "medium"
    return "small"


def probe(root: str | os.PathLike[str] = "/") -> HardwareProfile:
    cpu_threads = os.cpu_count() or 1
    cpu_cores = max(1, cpu_threads // 2)
    try:
        physical = os.sysconf("SC_NPROCESSORS_ONLN")
        cpu_threads = max(1, int(physical))
        cpu_cores = cpu_threads
    except (OSError, ValueError, AttributeError):
        pass
    gpu, gpu_vram = _gpu_info()
    ram = _ram_gb()
    try:
        disk_free = round(shutil.disk_usage(root).free / (1024**3), 2)
    except OSError:
        disk_free = 0.0
    tier = classify(ram, cpu_threads, gpu_vram)
    return HardwareProfile(
        architecture=platform.machine() or "unknown",
        os_name=platform.system() or "unknown",
        kernel=platform.release() or "unknown",
        cpu_model=_cpu_model(),
        cpu_cores=cpu_cores,
        cpu_threads=cpu_threads,
        cpu_mhz=_cpu_mhz(),
        ram_gb=ram,
        disk_free_gb=disk_free,
        gpu=gpu,
        gpu_vram_gb=gpu_vram,
        tier=tier,
    )


__all__ = ["HardwareProfile", "classify", "probe"]
