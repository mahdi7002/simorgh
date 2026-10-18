from __future__ import annotations

import json
import os
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "SIMORGH_MOTHER_PROJECT_AUDIT_V2"

SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "target", "dist", "build",
    ".venv", "venv", "__pycache__", ".cache", ".npm", ".cargo", ".rustup",
    ".local", ".config", ".mozilla", ".var", "snap", "proc", "sys", "dev",
    ".tox", ".mypy_cache", ".pytest_cache", ".gradle", ".idea", ".vscode",
}

STRONG_MARKERS = (
    "project.godot", "pyproject.toml", "setup.py", "requirements.txt",
    "package.json", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "build.gradle.kts", "Dockerfile", "docker-compose.yml", "compose.yml",
    "flake.nix", "mise.toml", ".mise.toml", "devbox.json", "flox.toml",
    ".devcontainer.json",
)
BUILD_MARKERS = ("Makefile", "CMakeLists.txt")


@dataclass(frozen=True)
class Check:
    kind: str
    command: tuple[str, ...]
    reason: str


def _run(root: Path, command: tuple[str, ...], timeout: int) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            list(command), cwd=root, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, timeout=timeout, check=False,
        )
        return {
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "command": list(command),
            "output": proc.stdout[-30000:],
        }
    except FileNotFoundError as exc:
        return {"status": "SKIPPED", "reason": f"missing executable: {exc.filename}", "command": list(command)}
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        return {
            "status": "FAIL", "returncode": None, "command": list(command),
            "output": str(output)[-30000:], "reason": f"timeout after {timeout}s",
        }
    except OSError as exc:
        return {"status": "FAIL", "command": list(command), "output": "", "reason": str(exc)}


def _git(root: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), *args], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=10, check=False,
        )
        return proc.stdout.strip() if proc.returncode == 0 else None
    except OSError:
        return None


def git_root(root: Path) -> Path | None:
    value = _git(root, "rev-parse", "--show-toplevel")
    if not value:
        return None
    return Path(value).resolve()


def is_git_repo(root: Path) -> bool:
    return git_root(root) is not None


def detect_contract(root: Path) -> dict[str, Any]:
    present = [m for m in (*STRONG_MARKERS, *BUILD_MARKERS) if (root / m).exists()]
    contracts: list[str] = []
    if (root / "project.godot").exists(): contracts.append("godot")
    if any((root / x).exists() for x in ("pyproject.toml", "setup.py", "requirements.txt")): contracts.append("python")
    if (root / "package.json").exists(): contracts.append("node")
    if (root / "Cargo.toml").exists(): contracts.append("rust")
    if (root / "go.mod").exists(): contracts.append("go")
    if any((root / x).exists() for x in ("pom.xml", "build.gradle", "build.gradle.kts")): contracts.append("jvm")
    if any((root / x).exists() for x in BUILD_MARKERS): contracts.append("native-build")
    if (root / "flake.nix").exists(): contracts.append("nix")
    if any((root / x).exists() for x in ("mise.toml", ".mise.toml")): contracts.append("mise")
    if (root / "devbox.json").exists(): contracts.append("devbox")
    if (root / "flox.toml").exists(): contracts.append("flox")
    if (root / ".devcontainer.json").exists() or (root / ".devcontainer" / "devcontainer.json").exists(): contracts.append("devcontainer")
    if any((root / x).exists() for x in ("Dockerfile", "docker-compose.yml", "compose.yml")): contracts.append("container")
    return {"marker_files": present, "contracts": sorted(set(contracts))}


def project_identity(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"name": root.name, "source": "directory_name"}
    for filename, section in (("pyproject.toml", "project"), ("Cargo.toml", "package")):
        path = root / filename
        if path.exists():
            try:
                data = tomllib.loads(path.read_text(encoding="utf-8"))
                name = (data.get(section) or {}).get("name")
                if isinstance(name, str) and name:
                    return {"name": name, "source": filename}
            except (OSError, tomllib.TOMLDecodeError):
                pass
    package = root / "package.json"
    if package.exists():
        try:
            name = json.loads(package.read_text(encoding="utf-8")).get("name")
            if isinstance(name, str) and name:
                return {"name": name, "source": "package.json"}
        except (OSError, json.JSONDecodeError):
            pass
    return result


def lifecycle_hint(root: Path) -> str:
    words = ("backup", "archive", "archived", "old", "pre-", "superseded", "مسیر قبل")
    haystack = "/".join(root.parts).lower()
    return "ARCHIVE_CANDIDATE" if any(word in haystack for word in words) else "ACTIVE_CANDIDATE"


def _package_test(root: Path) -> Check | None:
    path = root / "package.json"
    if not path.exists(): return None
    try: payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return None
    if "test" not in (payload.get("scripts") or {}): return None
    if (root / "pnpm-lock.yaml").exists(): return Check("node-test", ("pnpm", "test"), "package.json scripts.test")
    if (root / "yarn.lock").exists(): return Check("node-test", ("yarn", "test"), "package.json scripts.test")
    return Check("node-test", ("npm", "test"), "package.json scripts.test")



def _python_interpreter(root: Path) -> tuple[str, str]:
    """Resolve the target project's Python before falling back to Mother's Python."""
    candidates = (
        (".venv/bin/python", "project_venv"),
        ("venv/bin/python", "project_venv"),
        ("env/bin/python", "project_venv"),
    )

    for relative, source in candidates:
        candidate = root / relative
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate), source

    return sys.executable, "mother_python_fallback"


def _python_test(root: Path) -> Check | None:
    if not any((root / x).exists() for x in ("pyproject.toml", "setup.py", "requirements.txt")): return None
    if not (root / "tests").exists() and not (root / "test").exists(): return None

    executable, runtime_source = _python_interpreter(root)

    return Check(
        "python-test",
        (executable, "-m", "pytest", "-q"),
        f"Python project with tests/; runtime={runtime_source}",
    )


def _make_test(root: Path) -> Check | None:
    path = root / "Makefile"
    if not path.exists(): return None
    try: text = path.read_text(encoding="utf-8", errors="replace")
    except OSError: return None
    if "\ntest:" in text or text.startswith("test:"): return Check("make-test", ("make", "test"), "Makefile test target")
    return None


def checks_for(root: Path) -> list[Check]:
    checks: list[Check] = []
    contract = detect_contract(root)
    if "python" in contract["contracts"]:
        check = _python_test(root)
        if check: checks.append(check)
    check = _package_test(root)
    if check: checks.append(check)
    if "rust" in contract["contracts"]: checks.append(Check("rust-test", ("cargo", "test", "--all-targets"), "Cargo project"))
    if "go" in contract["contracts"]: checks.append(Check("go-test", ("go", "test", "./..."), "Go module"))
    check = _make_test(root)
    if check: checks.append(check)
    if "godot" in contract["contracts"]:
        checks.append(Check("godot-parse", ("godot", "--headless", "--path", str(root), "--editor", "--quit"), "Godot project parse/editor smoke test"))
    if (root / "docker-compose.yml").exists():
        checks.append(Check("compose-config", ("docker", "compose", "config", "--quiet"), "Docker Compose configuration validation"))
    return checks


def verification_plan(root: Path) -> list[dict[str, Any]]:
    contract = detect_contract(root)
    plan = [
        {"kind": c.kind, "command": list(c.command), "safe_default": True, "reason": c.reason}
        for c in checks_for(root)
    ]
    if "native-build" in contract["contracts"] and not any(x["kind"] == "make-test" for x in plan):
        plan.append({"kind": "native-build", "command": ["NOT_RUN_AUTOMATICALLY"], "safe_default": False, "reason": "CMake/Make project without a declared test target."})
    if "node" in contract["contracts"] and not any(x["kind"] == "node-test" for x in plan):
        plan.append({"kind": "node-test", "command": ["NO_TEST_SCRIPT"], "safe_default": False, "reason": "package.json has no scripts.test."})
    return plan


def repairability(check_result: dict[str, Any]) -> dict[str, Any]:
    if check_result.get("status") != "FAIL": return {"deterministic": [], "agent": False}
    out = str(check_result.get("output", ""))
    deterministic: list[str] = []
    if "SyntaxError" in out or "IndentationError" in out: deterministic.append("python-syntax-diagnosis")
    if "ruff" in out and "error" in out.lower(): deterministic.append("ruff-fix-candidate")
    return {"deterministic": deterministic, "agent": True, "note": "Agent repair requires backup and explicit permission."}


def audit_project(root: str | Path, *, execute: bool = False, timeout: int = 120) -> dict[str, Any]:
    root = Path(root).expanduser().resolve()
    repo = git_root(root) if root.exists() and root.is_dir() else None
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "path": str(root),
        "exists": root.exists(),
        "is_directory": root.is_dir(),
        "is_git_repository": repo is not None,
        "repository_root": str(repo) if repo else None,
        "project_kind": "repository" if repo == root else "nested_project" if repo else "standalone_project",
        "lifecycle": lifecycle_hint(root),
        "identity": project_identity(root) if root.exists() and root.is_dir() else {"name": root.name},
        "contract": detect_contract(root) if root.exists() and root.is_dir() else {"marker_files": [], "contracts": []},
        "verification_plan": [], "checks": [],
    }
    if not root.exists() or not root.is_dir():
        row["health"] = "UNAVAILABLE"; return row
    row["verification_plan"] = verification_plan(root)
    if not execute:
        row["checks"] = [{"kind": c.kind, "command": list(c.command), "reason": c.reason, "status": "NOT_RUN"} for c in checks_for(root)]
        row["health"] = "NOT_RUN" if row["checks"] else "NO_CHECK_DEFINED"
        return row
    results = []
    for check in checks_for(root):
        result = _run(root, check.command, timeout)
        result.update({"kind": check.kind, "reason": check.reason, "repairability": repairability(result)})
        results.append(result)
        if result["status"] == "FAIL": break
    row["checks"] = results
    if not results: row["health"] = "NO_CHECK_DEFINED"
    elif all(x["status"] == "PASS" for x in results): row["health"] = "PASS"
    elif any(x["status"] == "FAIL" for x in results): row["health"] = "FAIL"
    else: row["health"] = "DEGRADED"
    return row


def _children(path: Path) -> list[Path]:
    try: items = sorted(path.iterdir(), key=lambda p: p.name.lower())
    except OSError: return []
    return [p for p in items if p.is_dir() and p.name not in SKIP_DIRS and not p.is_symlink()]


def _strong_marker(path: Path) -> bool:
    return any((path / m).exists() for m in STRONG_MARKERS)


def _build_marker(path: Path) -> bool:
    return any((path / m).exists() for m in BUILD_MARKERS)


def discover_projects(roots: Iterable[str | Path], *, max_projects: int = 250, max_depth: int = 8) -> list[Path]:
    """
    Repository-aware discovery.

    Git roots are project boundaries. Inside a Git repository, ordinary
    CMakeLists/Makefiles are components, not projects. A nested directory
    becomes a project only with a strong project contract. Descendants of a
    nested project are suppressed unless they establish their own Git root.
    """
    found: list[Path] = []
    seen: set[Path] = set()

    for raw in roots:
        base = Path(raw).expanduser().resolve()
        if not base.exists() or not base.is_dir(): continue
        stack: list[tuple[Path, int, Path | None, Path | None]] = [(base, 0, None, None)]

        while stack and len(found) < max_projects:
            current, depth, repo_root, project_root = stack.pop()
            if current in seen or depth > max_depth: continue
            seen.add(current)

            git_boundary = (current / ".git").exists()
            if git_boundary:
                repo_root = current
                project_root = None
                if current not in found: found.append(current)
            elif repo_root is None:
                if _strong_marker(current) or _build_marker(current):
                    if current not in found: found.append(current)
                    project_root = current
            elif project_root is None:
                if _strong_marker(current):
                    if current not in found: found.append(current)
                    project_root = current

            for child in reversed(_children(current)):
                stack.append((child, depth + 1, repo_root, project_root))

    return sorted(set(found), key=lambda p: str(p))[:max_projects]


def audit_system(roots: Iterable[str | Path], *, execute: bool = False, timeout: int = 120, max_projects: int = 250) -> dict[str, Any]:
    projects = discover_projects(roots, max_projects=max_projects)
    rows = [audit_project(p, execute=execute, timeout=timeout) for p in projects]
    health_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    lifecycle_counts: dict[str, int] = {}
    for row in rows:
        for key, bucket in (("health", health_counts), ("project_kind", kind_counts), ("lifecycle", lifecycle_counts)):
            value = row.get(key, "UNKNOWN")
            bucket[value] = bucket.get(value, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "roots": [str(Path(x).expanduser().resolve()) for x in roots],
        "project_count": len(rows),
        "health_counts": health_counts,
        "project_kind_counts": kind_counts,
        "lifecycle_counts": lifecycle_counts,
        "projects": rows,
    }
