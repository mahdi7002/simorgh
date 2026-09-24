from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import psutil

from core.paths import ROOT
from core.user_runtime import DEFAULT_RUNTIME_DIR


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cmd(args: list[str], timeout: float = 3.0) -> tuple[int, str, str]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:
        return 127, "", str(exc)


def _boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
    except OSError:
        return "boot-unknown"


def _systemd_units() -> dict[str, Any]:
    rc, out, err = _cmd(
        ["systemctl", "list-units", "--all", "--type=service", "--no-legend", "--no-pager"],
        timeout=5,
    )
    units = {}
    if rc != 0:
        return {"available": False, "error": err or "systemctl unavailable", "units": units}
    for line in out.splitlines():
        parts = line.split(None, 4)
        if len(parts) >= 4:
            units[parts[0]] = {
                "load": parts[1],
                "active": parts[2],
                "sub": parts[3],
                "description": parts[4] if len(parts) > 4 else "",
            }
    return {"available": True, "units": units}


def _ports() -> list[dict[str, Any]]:
    rc, out, err = _cmd(["ss", "-lntup"], timeout=5)
    if rc != 0:
        return [{"status": "NOT_AVAILABLE", "error": err or "ss unavailable"}]
    rows = []
    for line in out.splitlines():
        if not line or line.startswith("Netid"):
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        local = parts[4]
        process = parts[6] if len(parts) > 6 else ""
        rows.append({"local": local, "process": process})
    return rows


def _processes() -> list[dict[str, Any]]:
    rows = []
    for proc in psutil.process_iter(["pid", "name", "username", "status", "cpu_percent", "memory_info", "cmdline"]):
        try:
            info = proc.info
            rss = (info.get("memory_info").rss if info.get("memory_info") else 0)
            cmdline = " ".join(info.get("cmdline") or [])[:500]
            rows.append(
                {
                    "pid": info["pid"],
                    "name": info.get("name"),
                    "user": info.get("username"),
                    "status": info.get("status"),
                    "cpu_percent": round(float(info.get("cpu_percent") or 0.0), 2),
                    "rss_mb": round(rss / 1024 / 1024, 2),
                    "cmdline": cmdline,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    rows.sort(key=lambda x: (x["rss_mb"], x["cpu_percent"]), reverse=True)
    return rows[:40]


def _repo_state(path: Path) -> dict[str, Any]:
    if not (path / ".git").exists():
        return {"path": str(path), "exists": path.exists(), "git": False}
    rc1, branch, _ = _cmd(["git", "-C", str(path), "branch", "--show-current"])
    rc2, head, _ = _cmd(["git", "-C", str(path), "rev-parse", "HEAD"])
    rc3, status, _ = _cmd(["git", "-C", str(path), "status", "--short", "--branch"], timeout=5)
    rc4, origin, _ = _cmd(["git", "-C", str(path), "rev-parse", "origin/main"], timeout=5)
    return {
        "path": str(path),
        "git": rc1 == 0,
        "branch": branch,
        "head": head,
        "origin_main": origin if rc4 == 0 else None,
        "status": status,
    }


def _runtime_files() -> list[dict[str, Any]]:
    rows = []
    roots = [
        DEFAULT_RUNTIME_DIR / "data",
        DEFAULT_RUNTIME_DIR / "memory",
        DEFAULT_RUNTIME_DIR / "logs",
        DEFAULT_RUNTIME_DIR / "mother",
    ]
    for root in roots:
        if not root.exists():
            continue
        try:
            for path in root.glob("*"):
                if path.is_file():
                    st = path.stat()
                    rows.append(
                        {
                            "path": str(path),
                            "size": st.st_size,
                            "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                        }
                    )
        except OSError:
            continue
    rows.sort(key=lambda x: x["mtime"], reverse=True)
    return rows[:200]


class SystemObserver:
    """Read-only snapshot collector. Permission gaps are recorded, not guessed."""

    def capture(self) -> dict[str, Any]:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        disk = psutil.disk_usage("/")
        load = getattr(os, "getloadavg", lambda: (0.0, 0.0, 0.0))()
        cpu_freq = psutil.cpu_freq()
        return {
            "timestamp": _now(),
            "boot_id": _boot_id(),
            "host": socket.gethostname(),
            "os": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "cpu": {
                "logical": psutil.cpu_count(logical=True),
                "physical": psutil.cpu_count(logical=False),
                "percent": psutil.cpu_percent(interval=0.1),
                "loadavg": [round(float(x), 3) for x in load],
                "freq_mhz": round(cpu_freq.current, 1) if cpu_freq else None,
            },
            "memory": {
                "total_mb": round(vm.total / 1024 / 1024, 1),
                "used_mb": round(vm.used / 1024 / 1024, 1),
                "available_mb": round(vm.available / 1024 / 1024, 1),
                "percent": vm.percent,
            },
            "swap": {
                "total_mb": round(swap.total / 1024 / 1024, 1),
                "used_mb": round(swap.used / 1024 / 1024, 1),
                "percent": swap.percent,
            },
            "disk": {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percent": disk.percent,
            },
            "systemd": _systemd_units(),
            "ports": _ports(),
            "processes": _processes(),
            "repositories": {
                "simorgh": _repo_state(ROOT),
                "agent_lab": _repo_state(Path.home() / "simorgh-agent-lab"),
                "legacy": _repo_state(Path.home() / "SimorghCore"),
            },
            "runtime_files": _runtime_files(),
        }


    def journal_since(self, since_iso: str, limit: int = 2000) -> dict[str, Any]:
        rc, out, err = _cmd(
            ["journalctl", "--since", since_iso, "--no-pager", "-o", "short-iso"],
            timeout=10,
        )
        if rc != 0:
            return {"status": "NOT_AVAILABLE", "error": err or "journalctl failed"}
        lines = []
        for line in out.splitlines():
            low = line.lower()
            if (
                "simorgh" in low
                or "llama-server" in low
                or "full reflection" in low
                or "mother" in low
                or ("systemd[1]:" in low and any(token in low for token in (
                    "started ", "stopped ", "failed ", "starting ", "stopping "
                )))
            ):
                lines.append(line)
        truncated = len(lines) > limit
        if truncated:
            lines = lines[:limit]
        return {
            "status": "OK",
            "count": len(lines),
            "truncated": truncated,
            "lines": lines,
        }
