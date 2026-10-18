from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from typing import Any

from .problem_memory import ProblemMemory


@dataclass(frozen=True)
class ResourceThresholds:
    memory_pressure_pct: float = 85.0
    memory_emergency_pct: float = 95.0
    swap_pressure_pct: float = 50.0
    swap_emergency_pct: float = 85.0
    disk_pressure_pct: float = 85.0
    disk_emergency_pct: float = 95.0
    cpu_pressure_pct: float = 85.0
    cpu_emergency_pct: float = 97.0


@dataclass
class ResourceSnapshot:
    timestamp: str
    state: str
    cpu_percent: float | None
    load1: float | None
    memory_total_bytes: int | None
    memory_available_bytes: int | None
    memory_used_pct: float | None
    swap_total_bytes: int | None
    swap_free_bytes: int | None
    swap_used_pct: float | None
    disk_total_bytes: int | None
    disk_free_bytes: int | None
    disk_used_pct: float | None
    mother: dict[str, Any]
    llama_server: dict[str, Any]
    ports: dict[str, bool]
    systemd: dict[str, str]
    pressure_signals: list[str]
    notes: list[str]


class ResourceManager:
    """Lightweight deterministic resource monitor. No LLM, no auto-repair, no source mutation."""

    _shared: "ResourceManager | None" = None
    _shared_lock = threading.Lock()

    def __init__(self, *, interval_seconds: float = 30.0, monitored_path: str | Path | None = None,
                 mother_port: int = 8011, fast_llm_port: int = 8080, quality_llm_port: int = 8081,
                 thresholds: ResourceThresholds | None = None, problem_memory: ProblemMemory | None = None) -> None:
        self.interval_seconds = max(5.0, float(interval_seconds))
        self.monitored_path = Path(monitored_path or Path.home())
        self.mother_port = int(mother_port)
        self.fast_llm_port = int(fast_llm_port)
        self.quality_llm_port = int(quality_llm_port)
        self.thresholds = thresholds or ResourceThresholds()
        self.problem_memory = problem_memory or ProblemMemory.shared()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._latest: ResourceSnapshot | None = None
        self._prev_cpu: tuple[int, int, float] | None = None
        self._prev_proc_cpu: dict[int, tuple[int, float]] = {}
        self._active_problem_keys: set[str] = set()
        self._last_problem_persist: dict[str, float] = {}
        self._previous_state = "NORMAL"
        self._previous_pressure_score = 0

    @classmethod
    def shared(cls, **kwargs: Any) -> "ResourceManager":
        with cls._shared_lock:
            if cls._shared is None:
                cls._shared = cls(**kwargs)
            return cls._shared

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, name="simorgh-resource-manager", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def latest(self) -> ResourceSnapshot | None:
        with self._lock:
            return self._latest

    def observe_once(self) -> ResourceSnapshot:
        now = datetime.now(timezone.utc).isoformat()
        cpu_percent, load1 = self._read_cpu()
        memory = self._read_memory()
        swap = self._read_swap()
        disk = self._read_disk()
        mother = self._find_process(("core.mother.server", "simorgh-mother"))
        llama = self._find_process(("llama-server",))
        ports = {
            str(self.mother_port): self._port_listening(self.mother_port),
            str(self.fast_llm_port): self._port_listening(self.fast_llm_port),
            str(self.quality_llm_port): self._port_listening(self.quality_llm_port),
        }
        systemd = {
            "simorgh-mother.service": self._systemd_state("simorgh-mother.service"),
            "llama-server.service": self._systemd_state("llama-server.service"),
        }
        state, signals, notes = self._classify(cpu_percent, memory["used_pct"], swap["used_pct"], disk["used_pct"])
        stable_keys = {self._stable_signal(s) for s in signals}
        self._record_pressure_changes(stable_keys, signals, state, memory, swap, disk)
        snapshot = ResourceSnapshot(
            timestamp=now, state=state, cpu_percent=cpu_percent, load1=load1,
            memory_total_bytes=memory["total"], memory_available_bytes=memory["available"], memory_used_pct=memory["used_pct"],
            swap_total_bytes=swap["total"], swap_free_bytes=swap["free"], swap_used_pct=swap["used_pct"],
            disk_total_bytes=disk["total"], disk_free_bytes=disk["free"], disk_used_pct=disk["used_pct"],
            mother=mother, llama_server=llama, ports=ports, systemd=systemd,
            pressure_signals=signals, notes=notes,
        )
        with self._lock:
            self._latest = snapshot
        return snapshot

    def snapshot_dict(self) -> dict[str, Any]:
        snap = self.latest() or self.observe_once()
        result = asdict(snap)
        result["resource_manager"] = {
            "interval_seconds": self.interval_seconds,
            "monitored_path": str(self.monitored_path),
            "llm_calls": 0,
            "automatic_repairs": 0,
        }
        result["problem_memory"] = self.problem_memory.context(limit=3)
        return result

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.observe_once()
            except Exception as exc:
                try:
                    self.problem_memory.record_incident(
                        component="resource-manager",
                        failure_type="resource_monitor_error",
                        severity="ERROR",
                        detected_by="resource_manager",
                        symptom=f"{type(exc).__name__}: {exc}",
                        signature={"error_type": type(exc).__name__},
                        evidence={"error": str(exc)[:1000]},
                    )
                except Exception:
                    pass
                with self._lock:
                    self._latest = ResourceSnapshot(
                        timestamp=datetime.now(timezone.utc).isoformat(), state="DEGRADED",
                        cpu_percent=None, load1=None, memory_total_bytes=None, memory_available_bytes=None,
                        memory_used_pct=None, swap_total_bytes=None, swap_free_bytes=None, swap_used_pct=None,
                        disk_total_bytes=None, disk_free_bytes=None, disk_used_pct=None, mother={}, llama_server={},
                        ports={}, systemd={}, pressure_signals=["resource_monitor_error"], notes=[f"{type(exc).__name__}: {exc}"],
                    )
            self._stop.wait(self.interval_seconds)

    def _read_cpu(self) -> tuple[float | None, float | None]:
        try:
            fields = Path("/proc/stat").read_text(encoding="utf-8", errors="replace").splitlines()[0].split()[1:]
            values = [int(v) for v in fields]
            total = sum(values)
            idle = values[3] + (values[4] if len(values) > 4 else 0)
        except (OSError, ValueError, IndexError):
            total = idle = None
        try:
            load1 = os.getloadavg()[0]
        except (OSError, IndexError):
            load1 = None
        if total is None or idle is None:
            return None, load1
        now = time.monotonic()
        previous = self._prev_cpu
        self._prev_cpu = (total, idle, now)
        if previous is None:
            return None, load1
        pt, pi, pn = previous
        dt = total - pt
        di = idle - pi
        wall = now - pn
        if dt <= 0 or wall <= 0:
            return None, load1
        return round(max(0.0, min(100.0, (dt - di) * 100.0 / dt)), 2), load1

    @staticmethod
    def _read_meminfo() -> dict[str, int]:
        out: dict[str, int] = {}
        try:
            lines = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return out
        for line in lines:
            m = re.match(r"^([A-Za-z0-9_]+):\s+(\d+)\s+kB$", line)
            if m:
                out[m.group(1)] = int(m.group(2)) * 1024
        return out

    def _read_memory(self) -> dict[str, int | float | None]:
        d = self._read_meminfo()
        total, available = d.get("MemTotal"), d.get("MemAvailable")
        used = round((1 - available / total) * 100, 2) if total and available is not None else None
        return {"total": total, "available": available, "used_pct": used}

    def _read_swap(self) -> dict[str, int | float | None]:
        d = self._read_meminfo()
        total, free = d.get("SwapTotal"), d.get("SwapFree")
        used = round((total - free) * 100 / total, 2) if total and free is not None else None
        return {"total": total, "free": free, "used_pct": used}

    def _read_disk(self) -> dict[str, int | float | None]:
        try:
            usage = shutil.disk_usage(self.monitored_path)
        except OSError:
            return {"total": None, "free": None, "used_pct": None}
        used = round(usage.used * 100 / usage.total, 2) if usage.total else None
        return {"total": usage.total, "free": usage.free, "used_pct": used}

    def _find_process(self, matchers: tuple[str, ...]) -> dict[str, Any]:
        try:
            proc_entries = Path("/proc").iterdir()
        except OSError:
            return {"pid": None, "cmdline": None, "rss_bytes": None, "cpu_percent": None, "found": False}
        for entry in proc_entries:
            if not entry.name.isdigit():
                continue
            pid = int(entry.name)
            if pid == os.getpid():
                continue
            try:
                cmdline = entry.joinpath("cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
                if not cmdline or not any(m in cmdline for m in matchers):
                    continue
                return {
                    "pid": pid, "cmdline": cmdline[:500],
                    "rss_bytes": self._process_rss(entry / "status"),
                    "cpu_percent": self._process_cpu_percent(pid, entry / "stat"),
                    "found": True,
                }
            except (OSError, ValueError):
                continue
        return {"pid": None, "cmdline": None, "rss_bytes": None, "cpu_percent": None, "found": False}

    @staticmethod
    def _process_rss(status_path: Path) -> int | None:
        try:
            for line in status_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.startswith("VmRSS:"):
                    m = re.search(r"(\d+)\s+kB", line)
                    return int(m.group(1)) * 1024 if m else None
        except OSError:
            return None
        return None

    def _process_cpu_percent(self, pid: int, stat_path: Path) -> float | None:
        try:
            fields = stat_path.read_text(encoding="utf-8", errors="replace").split()
            if len(fields) < 17:
                return None
            ticks = int(fields[13]) + int(fields[14])
        except (OSError, ValueError, IndexError):
            return None
        now = time.monotonic()
        previous = self._prev_proc_cpu.get(pid)
        self._prev_proc_cpu[pid] = (ticks, now)
        if previous is None:
            return None
        prev_ticks, prev_time = previous
        dt = now - prev_time
        delta = ticks - prev_ticks
        if dt <= 0 or delta < 0:
            return None
        try:
            hz = int(os.sysconf("SC_CLK_TCK"))
        except (ValueError, OSError):
            hz = 100
        return round(max(0.0, (delta / max(1, hz)) / dt * 100.0), 2)

    @staticmethod
    def _port_listening(port: int) -> bool:
        wanted = f"{int(port):04X}"
        for path in (Path("/proc/net/tcp"), Path("/proc/net/tcp6")):
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]
            except OSError:
                continue
            for line in lines:
                parts = line.split()
                if len(parts) >= 4 and parts[1].rsplit(":", 1)[-1].upper() == wanted and parts[3] == "0A":
                    return True
        return False

    @staticmethod
    def _systemd_state(unit: str) -> str:
        try:
            p = subprocess.run(["systemctl", "is-active", unit], capture_output=True, text=True, timeout=1.5, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return "UNKNOWN"
        return p.stdout.strip() or "UNKNOWN"

    @staticmethod
    def _stable_signal(signal: str) -> str:
        return signal.rsplit(":", 1)[0]

    def _record_pressure_changes(self, stable_keys: set[str], signals: list[str], state: str,
                                 memory: dict[str, Any], swap: dict[str, Any], disk: dict[str, Any]) -> None:
        now = time.monotonic()
        evidence = {
            "state": state,
            "signals": signals,
            "memory_used_pct": memory.get("used_pct"),
            "swap_used_pct": swap.get("used_pct"),
            "disk_used_pct": disk.get("used_pct"),
        }
        for key in sorted(stable_keys):
            if key not in self._active_problem_keys or now - self._last_problem_persist.get(key, 0) >= 300:
                level = "EMERGENCY" if "=EMERGENCY" in key else "PRESSURE"
                self.problem_memory.record_incident(
                    component="system-resource",
                    failure_type="resource_pressure",
                    severity=level,
                    detected_by="resource_manager",
                    symptom=key,
                    signature={"signal": key},
                    evidence=evidence,
                )
                self._last_problem_persist[key] = now
        for key in sorted(self._active_problem_keys - stable_keys):
            self.problem_memory.recover_by_signature(
                component="system-resource",
                failure_type="resource_pressure",
                signature={"signal": key},
                verifier_type="resource_manager",
                evidence=evidence,
            )
        self._active_problem_keys = set(stable_keys)

    def _classify(self, cpu: float | None, memory: float | None, swap: float | None, disk: float | None) -> tuple[str, list[str], list[str]]:
        t = self.thresholds
        signals: list[str] = []
        notes: list[str] = []
        score = 0
        emergency = False
        for value, pressure, emergency_threshold, label in (
            (cpu, t.cpu_pressure_pct, t.cpu_emergency_pct, "cpu_pct"),
            (memory, t.memory_pressure_pct, t.memory_emergency_pct, "memory_used_pct"),
            (swap, t.swap_pressure_pct, t.swap_emergency_pct, "swap_used_pct"),
            (disk, t.disk_pressure_pct, t.disk_emergency_pct, "disk_used_pct"),
        ):
            if value is None:
                notes.append(f"{label}: unavailable")
            elif value >= emergency_threshold:
                emergency = True
                signals.append(f"{label}=EMERGENCY:{value:.2f}")
                score += 2
            elif value >= pressure:
                signals.append(f"{label}=PRESSURE:{value:.2f}")
                score += 1
        if emergency:
            state = "EMERGENCY"
        elif score >= 2:
            state = "PRESSURE"
        elif score == 1:
            state = "DEGRADED"
        else:
            state = "NORMAL"
        if self._previous_state in {"DEGRADED", "PRESSURE", "EMERGENCY"} and state == "NORMAL" and score < self._previous_pressure_score:
            state = "RECOVERY"
        self._previous_state = state
        self._previous_pressure_score = score
        if not signals:
            notes.append("no threshold crossed")
        return state, signals, notes


if __name__ == "__main__":
    print(json.dumps(ResourceManager.shared(interval_seconds=30).snapshot_dict(), ensure_ascii=False, indent=2, sort_keys=True))
