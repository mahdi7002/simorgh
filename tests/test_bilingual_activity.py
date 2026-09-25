from pathlib import Path
from contextlib import closing


def test_bilingual_event_has_fa_and_en(monkeypatch, tmp_path):
    from core.mother import bilingual_activity as ba

    monkeypatch.setenv(
        "SIMORGH_MOTHER_DB",
        str(tmp_path / "mother.db"),
    )

    payload = ba.record_bilingual_event(
        event_type="observer_started",
        actor="mother",
        action="start",
        severity="info",
        verified=True,
        provenance="system",
        data={"interval_seconds": 300},
    )

    assert payload["narration"]["fa"]
    assert payload["narration"]["en"]

    assert (
        "SIMORGH_MOTHER_BILINGUAL_ACTIVITY_V1"
        == payload["schema_version"]
    )

    assert Path(ba.activity_path()).exists()
    assert Path(ba.latest_path()).exists()


def test_secrets_are_redacted(monkeypatch, tmp_path):
    from core.mother import bilingual_activity as ba

    monkeypatch.setenv(
        "SIMORGH_MOTHER_DB",
        str(tmp_path / "mother.db"),
    )

    payload = ba.record_bilingual_event(
        event_type="test_event",
        actor="test",
        action="test",
        severity="info",
        verified=False,
        provenance="test",
        data={
            "api_key": "DO_NOT_STORE",
            "normal": "keep",
        },
    )

    assert payload["data"]["api_key"] == "[REDACTED]"
    assert payload["data"]["normal"] == "keep"


def test_default_policy_is_persian_first(monkeypatch, tmp_path):
    from core.mother import bilingual_activity as ba

    monkeypatch.setenv(
        "SIMORGH_MOTHER_DB",
        str(tmp_path / "mother.db"),
    )

    policy = ba.load_policy()

    assert policy["system_language"] == "fa"
    assert policy["interaction_language"] == "fa"
    assert policy["always_store"] == ["fa", "en"]
    assert policy["audience"] == "child"

def test_ledger_bridge_accepts_missing_provenance(monkeypatch, tmp_path):
    from core.mother.ledger import MotherLedger

    monkeypatch.setenv(
        "SIMORGH_MOTHER_DB",
        str(tmp_path / "mother.db"),
    )

    ledger = MotherLedger(tmp_path / "mother.db")

    event_id = ledger.record_event(
        component="test",
        event_type="boot_started",
        actor="mother",
        action="observe",
        severity="info",
        verified=True,
        provenance=None,
        data={"ok": True},
    )

    assert event_id

    import sqlite3

    with closing(sqlite3.connect(
        tmp_path / "mother.db"
    )) as conn:
        row = conn.execute(
            "SELECT provenance FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()

    assert row is not None
    assert row[0] == "system_observation"

def test_ledger_record_event_defaults_remain_compatible(
    monkeypatch,
    tmp_path,
):
    from core.mother.ledger import MotherLedger

    monkeypatch.setenv(
        "SIMORGH_MOTHER_DB",
        str(tmp_path / "sidecar.db"),
    )

    ledger = MotherLedger(tmp_path / "mother.db")

    event_id = ledger.record_event(
        component="test",
        event_type="example",
        actor="pytest",
        verified=True,
        data={"ok": True},
    )

    assert event_id

