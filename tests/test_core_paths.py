"""Tests for core/paths.py (mission M-0708ee).

core.paths creates runtime directories at import time, so every test reloads
the module with SIMORGH_* pointed at tmp_path. The real data/ and memory/
directories are never touched, and the module is restored afterwards.
"""
import importlib
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ENV_DIRS = {
    "SIMORGH_DATA_DIR": "data",
    "SIMORGH_MEMORY_DIR": "memory",
    "SIMORGH_AUDIO_OUT_DIR": "audio_out",
    "SIMORGH_IMPORTS_DIR": "imports",
    "SIMORGH_TRANSCRIPTS_DIR": "transcripts",
    "SIMORGH_LOG_DIR": "logs",
}
DERIVED_ENV = [
    "SIMORGH_SNAPSHOT_DIR", "SIMORGH_PROPOSAL_DIR", "SIMORGH_QURAN_DB",
    "SIMORGH_POETRY_DB", "SIMORGH_APP_DB", "SIMORGH_BOOKS_DB",
    "SIMORGH_LIBRARY_DB", "SIMORGH_MEMORY_DB", "SIMORGH_JOURNAL_DB",
    "SIMORGH_ACTIVITY_DB",
]


@pytest.fixture
def load(tmp_path, monkeypatch):
    was_imported = "core.paths" in sys.modules
    for var, sub in ENV_DIRS.items():
        monkeypatch.setenv(var, str(tmp_path / sub))
    for var in DERIVED_ENV:
        monkeypatch.delenv(var, raising=False)

    import core.paths as paths

    def _load(**env):
        for key, value in env.items():
            monkeypatch.setenv(key, str(value))
        return importlib.reload(paths)

    yield _load

    monkeypatch.undo()
    if was_imported:
        importlib.reload(paths)
    else:
        sys.modules.pop("core.paths", None)


def test_root_points_at_repository(load):
    paths = load()
    assert paths.ROOT == Path(paths.__file__).resolve().parents[1]
    assert (paths.ROOT / "core").is_dir()


def test_env_overrides_are_used(load, tmp_path):
    paths = load()
    assert paths.DATA_DIR == (tmp_path / "data").resolve()
    assert paths.MEMORY_DIR == (tmp_path / "memory").resolve()
    assert paths.AUDIO_OUT_DIR == (tmp_path / "audio_out").resolve()
    assert paths.IMPORTS_DIR == (tmp_path / "imports").resolve()
    assert paths.TRANSCRIPTS_DIR == (tmp_path / "transcripts").resolve()
    assert paths.LOG_DIR == (tmp_path / "logs").resolve()


def test_derived_paths_follow_data_dir(load, tmp_path):
    paths = load()
    data = (tmp_path / "data").resolve()
    assert paths.SNAPSHOT_DIR == data / "snapshots"
    assert paths.PROPOSAL_DIR == data / "reflection_proposals"
    assert paths.QURAN_DB == data / "grid" / "quran.db"
    assert paths.POETRY_DB == data / "simorgh_full.db"
    assert paths.APP_DB == data / "simorgh.db"
    assert paths.BOOKS_DB == data / "books.db"
    assert paths.LIBRARY_DB == data / "library_catalog.db"
    assert paths.ACTIVITY_DB == data / "activity.db"


def test_memory_dbs_follow_memory_dir(load, tmp_path):
    paths = load()
    memory = (tmp_path / "memory").resolve()
    assert paths.MEMORY_DB == memory / "short_term.db"
    assert paths.JOURNAL_DB == memory / "journal.db"


def test_import_creates_runtime_dirs(load):
    paths = load()
    for p in (paths.DATA_DIR, paths.MEMORY_DIR, paths.AUDIO_OUT_DIR,
              paths.IMPORTS_DIR, paths.TRANSCRIPTS_DIR, paths.LOG_DIR,
              paths.SNAPSHOT_DIR, paths.PROPOSAL_DIR):
        assert p.is_dir(), p


def test_ensure_runtime_dirs_recreates_missing(load):
    paths = load()
    shutil.rmtree(paths.MEMORY_DIR)
    shutil.rmtree(paths.SNAPSHOT_DIR)
    assert not paths.MEMORY_DIR.exists()
    assert paths.ensure_runtime_dirs() is None
    assert paths.MEMORY_DIR.is_dir()
    assert paths.SNAPSHOT_DIR.is_dir()


def test_ensure_runtime_dirs_is_idempotent(load):
    paths = load()
    paths.ensure_runtime_dirs()
    paths.ensure_runtime_dirs()
    assert paths.DATA_DIR.is_dir()
    assert paths.LOG_DIR.is_dir()


def test_env_var_with_tilde_is_expanded(load, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    paths = load(SIMORGH_DATA_DIR="~/custom_data")
    assert paths.DATA_DIR == (tmp_path / "custom_data").resolve()
    assert paths.DATA_DIR.is_dir()
