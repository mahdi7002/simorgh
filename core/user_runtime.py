"""Persistent per-user runtime state, kept outside the source tree by default."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_RUNTIME_DIR = Path(
    os.environ.get(
        "SIMORGH_RUNTIME_DIR",
        Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "simorgh",
    )
).expanduser().resolve()
CONFIG_DIR = Path(
    os.environ.get(
        "SIMORGH_CONFIG_DIR",
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "simorgh",
    )
).expanduser().resolve()
CONFIG_FILE = CONFIG_DIR / "runtime.json"
RUNTIME_DATA_DIR = DEFAULT_RUNTIME_DIR / "data"
RUNTIME_MEMORY_DIR = DEFAULT_RUNTIME_DIR / "memory"
RUNTIME_MODEL_DIR = DEFAULT_RUNTIME_DIR / "models"
RUNTIME_LOG_DIR = DEFAULT_RUNTIME_DIR / "logs"


def ensure_user_dirs() -> None:
    for path in (
        DEFAULT_RUNTIME_DIR,
        RUNTIME_DATA_DIR,
        RUNTIME_MEMORY_DIR,
        RUNTIME_MODEL_DIR,
        RUNTIME_LOG_DIR,
        CONFIG_DIR,
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_config(data: dict[str, Any]) -> dict[str, Any]:
    ensure_user_dirs()
    current = load_config()
    current.update(data)
    tmp = CONFIG_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CONFIG_FILE)
    return current


def runtime_snapshot() -> dict[str, Any]:
    ensure_user_dirs()
    config = load_config()
    return {
        "configured": bool(config.get("configured")),
        "runtime_dir": str(DEFAULT_RUNTIME_DIR),
        "data_dir": str(RUNTIME_DATA_DIR),
        "memory_dir": str(RUNTIME_MEMORY_DIR),
        "model_dir": str(RUNTIME_MODEL_DIR),
        "config_file": str(CONFIG_FILE),
        "config": config,
    }


__all__ = [
    "CONFIG_FILE",
    "DEFAULT_RUNTIME_DIR",
    "RUNTIME_DATA_DIR",
    "RUNTIME_MEMORY_DIR",
    "RUNTIME_MODEL_DIR",
    "RUNTIME_LOG_DIR",
    "ensure_user_dirs",
    "load_config",
    "save_config",
    "runtime_snapshot",
]
