from __future__ import annotations

import psutil


def get_sensor_status(_query: str) -> dict[str, float | int]:
    """Return bounded local system telemetry with no network access."""
    return {
        "cpu_percent": float(psutil.cpu_percent(interval=0.0)),
        "memory_percent": float(psutil.virtual_memory().percent),
        "disk_percent": float(psutil.disk_usage("/").percent),
        "cpu_count": int(psutil.cpu_count() or 0),
    }
