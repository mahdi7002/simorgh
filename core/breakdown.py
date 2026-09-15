from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from core.paths import ROOT

CATALOG_PATH = ROOT / "catalog.json"


def load_catalog(path: Path = CATALOG_PATH) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_breakdown(catalog_path: Path = CATALOG_PATH) -> Counter[str]:
    catalog = load_catalog(catalog_path)
    docs = catalog.get("standalone_docs_unique") or catalog.get("standalone_docs") or []
    home = str(Path.home())
    counter: Counter[str] = Counter()
    for d in docs:
        rel = d[len(home) + 1:] if d.startswith(home) else d
        top = rel.split("/", 1)[0] if rel else ""
        if top:
            counter[top] += 1
    return counter


def main() -> int:
    for name, count in build_breakdown().most_common(25):
        print(f"{count:5d}  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
