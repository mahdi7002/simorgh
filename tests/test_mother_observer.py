from __future__ import annotations

from core.mother.observer import SystemObserver


def test_observer_captures_basic_system_state():
    snapshot = SystemObserver().capture()
    assert snapshot["boot_id"]
    assert snapshot["cpu"]["logical"]
    assert "memory" in snapshot
    assert "disk" in snapshot
