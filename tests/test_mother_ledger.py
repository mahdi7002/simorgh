from __future__ import annotations

import json

from core.mother.ledger import MotherLedger


def test_boot_event_snapshot_report_goal_and_quarantine(tmp_path):
    ledger = MotherLedger(tmp_path / "mother.db")
    boot = ledger.begin_boot()

    assert boot["boot_id"]
    assert boot["previous_boot_id"] is None

    event_id = ledger.record_event(
        component="test",
        event_type="example",
        actor="pytest",
        verified=True,
        data={"ok": True},
    )
    assert event_id

    ledger.save_snapshot({"timestamp": "2026-09-24T00:00:00+00:00", "boot_id": boot["boot_id"], "cpu": {"percent": 1}})
    assert ledger.latest_snapshot()["cpu"]["percent"] == 1

    ledger.save_report("DAILY", "2026-09-24T00:00:00+00:00", "2026-09-24T01:00:00+00:00", {"events_total": 1})
    assert ledger.latest_report("DAILY")["events_total"] == 1

    goal = ledger.add_goal("آزمون مادر")
    assert ledger.list_goals()[0]["id"] == goal

    item = ledger.add_quarantine(
        source_url="https://example.org/a",
        source_domain="example.org",
        title="Example",
        content_type="text/plain",
        content="evidence",
    )
    q = ledger.get_quarantine(item)
    assert q["status"] == "QUARANTINED"
    assert q["content_sha256"]


def test_list_code_repairs_decodes_verification(tmp_path):
    ledger = MotherLedger(tmp_path / "mother.db")
    item_id = ledger.create_code_repair("fix test", "diff")
    ledger.update_code_repair(item_id, status="VERIFIED", verification={"status": "VERIFIED"})
    rows = ledger.list_code_repairs()
    assert rows[0]["id"] == item_id
    assert json.loads(json.dumps(rows[0]["verification"]))["status"] == "VERIFIED"
