#!/usr/bin/env python3
"""Strict public-repository audit for privacy leaks and fail-open compliance checks."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ABSOLUTE_PATH_PATTERNS = [
    re.compile(r"(?<![A-Za-z0-9_])/(?:home|root|Users|srv|var)/[A-Za-z0-9._~+@%-]+(?:/[A-Za-z0-9._~+@%-]+)*"),
    re.compile(r"(?:[A-Za-z]:\\\\Users\\\\|[A-Za-z]:/Users/)[^\s\"']+"),
]
SECRET_PATTERNS = [
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bsk-[A-Za-z0-9]{24,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{24,}\b"),
]
TEXT_EXTENSIONS = {
    ".py", ".sh", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".json", ".csv",
    ".md", ".txt", ".rst", ".xml", ".html", ".js", ".ts", ".css", ".sql",
}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return [p.decode("utf-8", "strict") for p in out.split(b"\0") if p]


def text_for(rel: str) -> str | None:
    path = ROOT / rel
    if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
        return None
    try:
        if path.stat().st_size > 4 * 1024 * 1024:
            return None
        return path.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeError):
        return None


def main() -> int:
    failures: list[str] = []
    files = tracked_files()

    for rel in files:
        text = text_for(rel)
        if text is None:
            continue
        for pattern in ABSOLUTE_PATH_PATTERNS:
            match = pattern.search(text)
            if match:
                failures.append(f"PUBLIC_PATH_LEAK:{rel}:{match.group(0)[:180]}")
                break
        for pattern in SECRET_PATTERNS:
            match = pattern.search(text)
            if match:
                failures.append(f"POSSIBLE_SECRET:{rel}:{match.group(0)[:24]}")
                break

    workflows = sorted((ROOT / ".github/workflows").glob("*.y*ml"))
    for path in workflows:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "permissions:" not in text:
            failures.append(f"WORKFLOW_PERMISSIONS_UNSPECIFIED:{path.relative_to(ROOT)}")

    signoff = ROOT / "compliance" / "RELEASE_SIGNOFF.md"
    if signoff.exists():
        text = signoff.read_text(encoding="utf-8", errors="ignore")
        if "Release decision: `APPROVED`" in text:
            failures.append("HUMAN_SIGNOFF_ALREADY_APPROVED_IN_REPOSITORY")

    if failures:
        print("STRICT PUBLIC SURFACE AUDIT: BLOCK")
        for failure in failures:
            print(failure)
        return 1

    print(json.dumps({"status": "PASS", "tracked_files": len(files), "workflows_checked": len(workflows)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
