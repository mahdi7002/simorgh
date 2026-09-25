from core.mother.observer import SystemObserver, _journalctl_since_arg


def test_journalctl_timestamp_normalizes_iso_utc_with_microseconds():
    value = "2026-09-25T02:57:58.330603+00:00"

    assert _journalctl_since_arg(value) == "2026-09-25 02:57:58 UTC"


def test_journalctl_timestamp_normalizes_zulu_timestamp():
    value = "2026-09-25T02:57:58.330603Z"

    assert _journalctl_since_arg(value) == "2026-09-25 02:57:58 UTC"


def test_journalctl_timestamp_converts_offset_to_utc():
    value = "2026-09-25T06:27:58.330603+03:30"

    assert _journalctl_since_arg(value) == "2026-09-25 02:57:58 UTC"


def test_journalctl_timestamp_keeps_unparseable_input_for_error_reporting():
    value = "NOT_A_TIMESTAMP"

    assert _journalctl_since_arg(value) == value


def test_journal_since_uses_normalized_timestamp(monkeypatch):
    captured = {}

    def fake_cmd(args, timeout=3.0):
        captured["args"] = args
        captured["timeout"] = timeout
        return 0, "journal-line", ""

    monkeypatch.setattr(
        "core.mother.observer._cmd",
        fake_cmd,
    )

    result = SystemObserver().journal_since(
        "2026-09-25T02:57:58.330603+00:00"
    )

    assert result["status"] == "OK"
    assert captured["args"] == [
        "journalctl",
        "--since",
        "2026-09-25 02:57:58 UTC",
        "--no-pager",
        "-n",
        "2000",
        "-o",
        "short-iso",
    ]
    assert captured["timeout"] == 10


def test_journal_current_boot_is_bounded(monkeypatch):
    captured = {}

    def fake_cmd(args, timeout=3.0):
        captured["args"] = args
        captured["timeout"] = timeout
        return 0, "journal-line", ""

    monkeypatch.setattr(
        "core.mother.observer._cmd",
        fake_cmd,
    )

    result = SystemObserver().journal_current_boot(limit=2000)

    assert result["status"] == "OK"
    assert captured["args"] == [
        "journalctl",
        "-b",
        "--no-pager",
        "-n",
        "2000",
        "-o",
        "short-iso",
    ]
    assert captured["timeout"] == 10
