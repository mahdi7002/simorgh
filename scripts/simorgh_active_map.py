#!/usr/bin/env python3
"""
SIMORGH ACTIVE MAP

Read-only repository scanner.

Design principles:
- no third-party dependencies
- never modifies project source
- never modifies databases
- never modifies git history
- evidence before verification
- UNKNOWN is a valid result
- COVERED != VERIFIED
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VERSION = "1.0.0"

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "target",
    "build",
    "dist",
    ".tox",
    ".eggs",
    "*.egg-info",
}

SOURCE_EXTENSIONS = {
    ".py",
    ".rs",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".java",
    ".kt",
    ".kts",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".cc",
    ".hh",
    ".swift",
}

TEST_NAME_PATTERNS = (
    "test_",
    "_test.",
    "tests/",
    "test/",
)

MODEL_EXTENSIONS = {
    ".gguf",
    ".onnx",
    ".safetensors",
    ".bin",
    ".pt",
    ".pth",
}

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key)\s*[:=]\s*[\"'][^\"']+[\"']"),
    re.compile(r"(?i)(secret|token|password)\s*[:=]\s*[\"'][^\"']+[\"']"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_git(root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def sha256_file(path: Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except Exception:
        return None


def should_ignore(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True

    for part in relative.parts:
        if part in IGNORE_DIRS:
            return True
    return False


def iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        current_path = Path(current)

        dirs[:] = [
            d for d in dirs
            if d not in IGNORE_DIRS
            and not d.endswith(".egg-info")
        ]

        for filename in files:
            path = current_path / filename
            if should_ignore(path, root):
                continue
            yield path


def is_test_file(path: Path, root: Path) -> bool:
    r = rel(root, path)
    name = path.name.lower()

    if any(part in {"tests", "test"} for part in Path(r).parts[:-1]):
        return True

    if name.startswith("test_"):
        return True

    if name.endswith("_test.py"):
        return True

    if name.endswith("_test.rs"):
        return True

    return False


def parse_python(path: Path, root: Path) -> dict[str, Any]:
    result = {
        "symbols": [],
        "imports": [],
        "parse_error": None,
    }

    try:
        source = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(path))
    except Exception as exc:
        result["parse_error"] = f"{type(exc).__name__}: {exc}"
        return result

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result["symbols"].append({
                "kind": "function",
                "name": node.name,
                "line": node.lineno,
            })

        elif isinstance(node, ast.ClassDef):
            result["symbols"].append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                result["imports"].append({
                    "kind": "import",
                    "name": alias.name,
                    "line": node.lineno,
                })

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            result["imports"].append({
                "kind": "from",
                "name": module,
                "line": node.lineno,
            })

    return result


def scan_source_file(path: Path, root: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "path": rel(root, path),
        "extension": path.suffix.lower(),
        "size_bytes": None,
        "sha256": None,
        "test_file": is_test_file(path, root),
        "symbols": [],
        "imports": [],
        "parse_error": None,
    }

    try:
        item["size_bytes"] = path.stat().st_size
    except OSError:
        pass

    item["sha256"] = sha256_file(path)

    if path.suffix.lower() == ".py":
        parsed = parse_python(path, root)
        item["symbols"] = parsed["symbols"]
        item["imports"] = parsed["imports"]
        item["parse_error"] = parsed["parse_error"]

    return item


def scan_repository(root: Path) -> dict[str, Any]:
    files = []
    source_files = []
    test_files = []
    models = []

    for path in iter_files(root):
        try:
            relative = rel(root, path)
        except ValueError:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            size = None

        suffix = path.suffix.lower()

        record = {
            "path": relative,
            "size_bytes": size,
        }

        if suffix in SOURCE_EXTENSIONS:
            source_record = scan_source_file(path, root)
            source_files.append(source_record)

            if source_record["test_file"]:
                test_files.append(source_record)

        elif suffix in MODEL_EXTENSIONS:
            models.append({
                "path": relative,
                "size_bytes": size,
                "sha256": sha256_file(path),
                "extension": suffix,
            })

        files.append(record)

    return {
        "files": files,
        "source_files": source_files,
        "test_files": test_files,
        "models": models,
    }


def git_snapshot(root: Path) -> dict[str, Any]:
    status = run_git(root, ["status", "--short", "--branch"])
    branch = run_git(root, ["branch", "--show-current"])
    head = run_git(root, ["rev-parse", "HEAD"])
    origin = run_git(root, ["rev-parse", "origin/main"])
    latest = run_git(root, ["log", "-1", "--format=%H%x00%h%x00%s"])

    ahead_behind_raw = run_git(
        root,
        ["rev-list", "--left-right", "--count", "origin/main...HEAD"],
    )

    ahead = None
    behind = None

    if ahead_behind_raw:
        parts = ahead_behind_raw.split()
        if len(parts) == 2:
            try:
                behind = int(parts[0])
                ahead = int(parts[1])
            except ValueError:
                pass

    latest_record = None
    if latest:
        parts = latest.split("\x00", 2)
        if len(parts) == 3:
            latest_record = {
                "sha": parts[0],
                "short_sha": parts[1],
                "subject": parts[2],
            }

    return {
        "is_git_repository": (root / ".git").exists(),
        "branch": branch,
        "head": head,
        "origin_main": origin,
        "ahead": ahead,
        "behind": behind,
        "latest_commit": latest_record,
        "status_porcelain": status,
    }


def runtime_snapshot(root: Path) -> dict[str, Any]:
    candidates = [
        "main.py",
        "pyproject.toml",
        "requirements.txt",
        "requirements-dev.txt",
        "requirements-optional.txt",
        "runtime.json",
        "config.json",
    ]

    present = []

    for item in candidates:
        path = root / item
        if path.exists():
            present.append(item)

    service_candidates = [
        Path.home() / ".config/systemd/user/simorgh.service",
        Path("/etc/systemd/system/simorgh-core.service"),
        Path("/etc/systemd/system/simorgh.service"),
    ]

    services = []

    for path in service_candidates:
        if path.exists():
            services.append(str(path))

    return {
        "python": sys.version,
        "executable": sys.executable,
        "cwd": str(root),
        "project_files": present,
        "service_files": services,
        "runtime_config": str(
            Path.home() / ".config/simorgh/runtime.json"
        ),
    }


def detect_capabilities(root: Path, source_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = {item["path"] for item in source_files}

    groups = {
        "local_runtime": [
            p for p in paths
            if "runtime" in p.lower()
            or "server" in p.lower()
            or "llm" in p.lower()
        ],
        "memory": [
            p for p in paths
            if "memory" in p.lower()
            or "history" in p.lower()
        ],
        "knowledge": [
            p for p in paths
            if "knowledge" in p.lower()
            or "source" in p.lower()
            or "poem" in p.lower()
            or "quran" in p.lower()
        ],
        "governance": [
            p for p in paths
            if any(
                token in p.lower()
                for token in (
                    "ethic",
                    "policy",
                    "govern",
                    "consent",
                    "autonomy",
                    "security",
                    "safety",
                )
            )
        ],
        "testing": [
            p for p in paths
            if "test" in p.lower()
        ],
        "bridge": [
            p for p in paths
            if "bridge" in p.lower()
        ],
    }

    capabilities = []

    for name, evidence in groups.items():
        if evidence:
            status = "DISCOVERED"
        else:
            status = "UNKNOWN"

        capabilities.append({
            "id": f"capability.{name}",
            "name": name,
            "status": status,
            "evidence": sorted(evidence)[:100],
        })

    return capabilities


def build_test_coverage(
    source_files: list[dict[str, Any]],
    test_files: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    test_paths = [item["path"] for item in test_files]

    result = []

    for source in source_files:
        if source["test_file"]:
            continue

        source_path = source["path"]
        stem = Path(source_path).stem

        candidates = [
            p for p in test_paths
            if stem in Path(p).stem
        ]

        if candidates:
            status = "COVERED"
            evidence = candidates[:20]
        else:
            status = "UNKNOWN"
            evidence = []

        result.append({
            "source": source_path,
            "status": status,
            "test_evidence": evidence,
        })

    return result


def build_missions(
    source_files: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    missions = []

    for item in coverage:
        if item["status"] == "UNKNOWN":
            missions.append({
                "id": "mission.test." + hashlib.sha1(
                    item["source"].encode()
                ).hexdigest()[:10],
                "type": "TEST_GAP",
                "status": "PROPOSED",
                "target": item["source"],
                "evidence": [],
                "reason": "No directly matching test file discovered.",
                "authority": "HUMAN_GATE_REQUIRED",
            })

    for capability in capabilities:
        if capability["status"] == "DISCOVERED":
            missions.append({
                "id": "mission.verify." + capability["id"],
                "type": "CAPABILITY_VERIFICATION",
                "status": "PROPOSED",
                "target": capability["id"],
                "evidence": capability["evidence"][:20],
                "reason": "Capability discovered but not independently verified by this scanner.",
                "authority": "HUMAN_GATE_REQUIRED",
            })

    return missions


def governance_snapshot(root: Path) -> dict[str, Any]:
    evidence = []

    for path in iter_files(root):
        if path.suffix.lower() not in {".py", ".rs", ".md", ".toml", ".yml", ".yaml", ".json"}:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        lower = text.lower()

        if any(
            token in lower
            for token in (
                "human_gate",
                "human gate",
                "proposal not command",
                "autonomy",
                "consent",
                "self_improvement_policy",
                "risklevel",
            )
        ):
            evidence.append(rel(root, path))

    return {
        "status": "DISCOVERED" if evidence else "UNKNOWN",
        "evidence": sorted(set(evidence)),
        "rules": {
            "proposal_not_command": "UNKNOWN",
            "human_gate": "UNKNOWN",
            "agent_can_mutate_memory": "UNKNOWN",
            "agent_can_change_constitution": "UNKNOWN",
            "provenance_required": "UNKNOWN",
        },
    }


def build_verification_summary(
    source_files: list[dict[str, Any]],
    coverage: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "principle": "COVERED != VERIFIED",
        "source_files_discovered": len(source_files),
        "coverage_records": len(coverage),
        "covered": sum(
            1 for item in coverage
            if item["status"] == "COVERED"
        ),
        "unknown": sum(
            1 for item in coverage
            if item["status"] == "UNKNOWN"
        ),
        "verified": 0,
        "note": "This scanner does not certify correctness.",
    }


def build_map(root: Path) -> dict[str, Any]:
    repository = scan_repository(root)

    capabilities = detect_capabilities(
        root,
        repository["source_files"],
    )

    coverage = build_test_coverage(
        repository["source_files"],
        repository["test_files"],
    )

    missions = build_missions(
        repository["source_files"],
        coverage,
        capabilities,
    )

    governance = governance_snapshot(root)

    git = git_snapshot(root)

    runtime = runtime_snapshot(root)

    return {
        "schema": "SIMORGH_ACTIVE_MAP_V1",
        "scanner": {
            "name": "simorgh_active_map.py",
            "version": VERSION,
            "mode": "READ_ONLY",
            "generated_at": utc_now(),
        },
        "repository": {
            "root": str(root),
            "relative_root": ".",
            "file_count": len(repository["files"]),
            "source_file_count": len(repository["source_files"]),
            "test_file_count": len(repository["test_files"]),
            "model_count": len(repository["models"]),
        },
        "git": git,
        "modules": repository["source_files"],
        "symbols": [
            {
                "file": item["path"],
                **symbol,
            }
            for item in repository["source_files"]
            for symbol in item["symbols"]
        ],
        "imports": [
            {
                "file": item["path"],
                **imp,
            }
            for item in repository["source_files"]
            for imp in item["imports"]
        ],
        "tests": {
            "files": [
                item["path"]
                for item in repository["test_files"]
            ],
            "coverage": coverage,
        },
        "models": repository["models"],
        "capabilities": capabilities,
        "governance": governance,
        "runtime": runtime,
        "verification": build_verification_summary(
            repository["source_files"],
            coverage,
        ),
        "missions": missions,
        "status": {
            "overall": "PARTIALLY_VERIFIED",
            "rule": "Never upgrade UNKNOWN to VERIFIED without evidence.",
        },
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Build a read-only SIMORGH Active Map."
    )

    parser.add_argument(
        "--root",
        default=".",
        help="SIMORGH repository root.",
    )

    parser.add_argument(
        "--output",
        default="active_map.json",
        help="Output JSON path.",
    )

    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON.",
    )

    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()

    if not root.exists():
        print(f"ERROR: repository root does not exist: {root}", file=sys.stderr)
        return 2

    if not root.is_dir():
        print(f"ERROR: repository root is not a directory: {root}", file=sys.stderr)
        return 2

    output = Path(args.output).expanduser()

    if not output.is_absolute():
        output = root / output

    output.parent.mkdir(parents=True, exist_ok=True)

    active_map = build_map(root)

    with output.open("w", encoding="utf-8") as f:
        json.dump(
            active_map,
            f,
            ensure_ascii=False,
            indent=2 if args.pretty else None,
            sort_keys=False,
        )
        f.write("\n")

    print()
    print("SIMORGH ACTIVE MAP")
    print("==================")
    print(f"Repository : {root}")
    print(f"Output     : {output}")
    print(f"Files      : {active_map['repository']['file_count']}")
    print(f"Source     : {active_map['repository']['source_file_count']}")
    print(f"Tests      : {active_map['repository']['test_file_count']}")
    print(f"Models     : {active_map['repository']['model_count']}")
    print(f"Symbols    : {len(active_map['symbols'])}")
    print(f"Imports    : {len(active_map['imports'])}")
    print(f"Capabilities: {len(active_map['capabilities'])}")
    print(f"Missions   : {len(active_map['missions'])}")
    print(f"Overall    : {active_map['status']['overall']}")
    print()
    print("READ-ONLY: no source/database/git mutation performed.")
    print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
