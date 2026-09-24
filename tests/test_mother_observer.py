from __future__ import annotations

from core.mother.observer import SystemObserver


def test_observer_captures_basic_system_state():
    snapshot = SystemObserver().capture()
    assert snapshot["boot_id"]
    assert snapshot["cpu"]["logical"]
    assert "memory" in snapshot
    assert "disk" in snapshot



def test_process_observer_counts_processes():
    snapshot = SystemObserver().capture()
    processes = snapshot["processes"]
    assert isinstance(processes["total_count"], int)
    assert processes["total_count"] >= len(processes["top"])
    assert len(processes["top"]) <= 40
