#!/usr/bin/env python3
"""Generate a deterministic inventory of shipped content assets.

The manifest records exact tracked paths, byte sizes and SHA-256 hashes. It does
not declare ownership or license rights; those remain a separate human review
obligation in compliance/ASSET_RIGHTS.csv.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ("data/", "quran/", "music/")
SPECIAL = {"catalog.json"}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return sorted(p for p in result.stdout.decode().split("\0") if p)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/simorgh-asset-manifest.json")
    args = parser.parse_args()

    assets = []
    for rel in tracked_files():
        if rel not in SPECIAL and not rel.startswith(PREFIXES):
            continue
        path = ROOT / rel
        if not path.is_file():
            continue
        assets.append(
            {
                "path": rel,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    document = {
        "schema": "simorgh.asset-manifest.v1",
        "rights_status": "NOT_VERIFIED",
        "asset_count": len(assets),
        "assets": assets,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Asset manifest written: {output} ({len(assets)} assets)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
