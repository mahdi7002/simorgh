from __future__ import annotations

from core.mother.resource_manager import ResourceManager
from core.mother.problem_memory import ProblemMemory


def test_normal_classification(tmp_path):
    rm = ResourceManager(problem_memory=ProblemMemory(tmp_path / "mother.db"))
    state, signals, _ = rm._classify(20, 40, 5, 50)
    assert state == "NORMAL"
    assert signals == []


def test_degraded_swap(tmp_path):
    rm = ResourceManager(problem_memory=ProblemMemory(tmp_path / "mother.db"))
    state, signals, _ = rm._classify(20, 60, 67, 50)
    assert state == "DEGRADED"
    assert signals == ["swap_used_pct=PRESSURE:67.00"]


def test_pressure_two_signals(tmp_path):
    rm = ResourceManager(problem_memory=ProblemMemory(tmp_path / "mother.db"))
    state, signals, _ = rm._classify(90, 90, 5, 50)
    assert state == "PRESSURE"
    assert len(signals) == 2


def test_emergency(tmp_path):
    rm = ResourceManager(problem_memory=ProblemMemory(tmp_path / "mother.db"))
    state, signals, _ = rm._classify(98, 40, 5, 50)
    assert state == "EMERGENCY"
    assert signals[0].startswith("cpu_pct=EMERGENCY:")


def test_first_process_cpu_is_unknown(tmp_path, monkeypatch):
    rm = ResourceManager(problem_memory=ProblemMemory(tmp_path / "mother.db"))
    p = tmp_path / "stat"
    p.write_text("0 0 0 0 0 0 0 0 0 0 0 0 100 0 0 0 0\n", encoding="utf-8")
    times = iter([10.0])
    monkeypatch.setattr("core.mother.resource_manager.time.monotonic", lambda: next(times))
    monkeypatch.setattr("core.mother.resource_manager.os.sysconf", lambda _: 100)
    assert rm._process_cpu_percent(123, p) is None
