from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


DEFAULT_CONFIG_PATH = Path.home() / ".config" / "simorgh" / "mother_repositories.json"


def resolve_repository_paths(
    repositories: Iterable[str | Path] | None = None,
    config_path: str | Path | None = None,
) -> list[Path]:
    """
    Resolve the repositories Mother should observe.

    Priority:
      1. Explicit repositories argument
      2. JSON config file
      3. Current working directory

    Missing config is intentionally not an error.
    Paths are resolved and deduplicated while preserving order.
    """
    if repositories is not None:
        raw = list(repositories)
    else:
        path = Path(config_path).expanduser() if config_path else DEFAULT_CONFIG_PATH
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            raw = payload.get("repositories", [])
            if not isinstance(raw, list):
                raise ValueError("mother repositories config: 'repositories' must be a list")
        else:
            raw = []

    if not raw:
        raw = [Path.cwd()]

    resolved: list[Path] = []
    seen: set[Path] = set()

    for item in raw:
        path = Path(item).expanduser().resolve()
        if path not in seen:
            resolved.append(path)
            seen.add(path)

    return resolved
