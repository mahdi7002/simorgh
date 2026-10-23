import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ensure_poetry_db.sh"


def _builder():
    spec = importlib.util.spec_from_file_location("build_verse_db", ROOT / "scripts" / "build_verse_db.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _source(tmp_path):
    root = tmp_path / "ganjoor"
    (root / "poets" / "testa").mkdir(parents=True)
    (root / "manifest.json").write_text(json.dumps(
        {"Poets": [{"Id": 1, "Nickname": "شاعر آزمون", "FullUrl": "/testa"}]}, ensure_ascii=False), encoding="utf-8")
    for i in range(60):
        verses = []
        for c in range(2):
            verses.append({"VOrder": 2 * c + 1, "Position": "Right", "Text": "مصرع نخست %d %d" % (i, c), "CoupletIndex": c})
            verses.append({"VOrder": 2 * c + 2, "Position": "Left", "Text": "مصرع دوم %d %d" % (i, c), "CoupletIndex": c})
        (root / "poets" / "testa" / ("p%d.json" % i)).write_text(json.dumps(
            {"FullTitle": "شاعر آزمون » غزلیات » شعر %d" % i, "Title": "شعر %d" % i, "Verses": verses}, ensure_ascii=False), encoding="utf-8")
    return root


def _run(db, *args, extra=None):
    env = dict(os.environ, SIMORGH_VERSE_DB=str(db), PYTHON=sys.executable, **(extra or {}))
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, env=env, timeout=120)


def test_syntax():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0


def test_healthy_database_means_nothing_is_downloaded(tmp_path):
    db = tmp_path / "v.db"
    _builder().build(_source(tmp_path), db, log=lambda *_a: None)
    r = _run(db, extra={"GANJOOR_SOURCE_DIR": str(tmp_path / "must-not-exist")})
    assert r.returncode == 0 and "already there" in r.stdout
    assert not (tmp_path / "must-not-exist").exists()


def test_missing_database_without_yes_stops_before_any_download(tmp_path):
    r = _run(tmp_path / "none.db", extra={"GANJOOR_SOURCE_DIR": str(tmp_path / "src")})
    assert r.returncode == 3 and "--yes" in r.stdout
    assert not (tmp_path / "src").exists()


def test_lfs_pointer_is_not_treated_as_healthy(tmp_path):
    db = tmp_path / "pointer.db"
    pointer = b"version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 1\n"
    db.write_bytes(pointer)
    r = _run(db, "--yes", extra={"GANJOOR_SOURCE_DIR": str(tmp_path / "src")})
    assert r.returncode == 8
    assert "refusing to overwrite" in (r.stdout + r.stderr)
    assert db.read_bytes() == pointer
    assert not (tmp_path / "src").exists()


def test_legacy_builder_version_is_not_accepted_or_overwritten(tmp_path):
    import sqlite3

    db = tmp_path / "legacy.db"
    _builder().build(_source(tmp_path), db, log=lambda *_a: None)

    conn = sqlite3.connect(db)
    try:
        conn.execute(
            "UPDATE build_info SET value='1' WHERE key='builder_version'"
        )
        conn.commit()
    finally:
        conn.close()

    r = _run(db, "--yes", extra={"GANJOOR_SOURCE_DIR": str(tmp_path / "src")})
    assert r.returncode == 8
    assert "refusing to overwrite" in (r.stdout + r.stderr)

    conn = sqlite3.connect(db)
    try:
        version = conn.execute(
            "SELECT value FROM build_info WHERE key='builder_version'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert version == "1"
    assert not (tmp_path / "src").exists()


def test_non_git_source_directory_is_never_removed(tmp_path):
    src = tmp_path / "existing-source"
    src.mkdir()
    sentinel = src / "keep-me.txt"
    sentinel.write_text("user data", encoding="utf-8")

    r = _run(
        tmp_path / "new.db",
        "--yes",
        extra={"GANJOOR_SOURCE_DIR": str(src)},
    )
    assert r.returncode == 5
    assert "left untouched" in (r.stdout + r.stderr)
    assert sentinel.read_text(encoding="utf-8") == "user data"


def test_setup_script_has_no_recursive_delete():
    assert "rm -rf" not in SCRIPT.read_text(encoding="utf-8")
