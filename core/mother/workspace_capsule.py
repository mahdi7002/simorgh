from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .workspace_inspector import SCHEMA_VERSION

CAPSULE_SCHEMA = "SIMORGH_MOTHER_WORKSPACE_CAPSULE_V1"
SECRET_NAME_PARTS = (
    ".env",
    "secret",
    "credential",
    "password",
    "passwd",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "id_rsa",
    ".pem",
    ".p12",
    ".pfx",
)


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
        timeout=20,
    )


def _text(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _safe_name(path: Path) -> str:
    raw = "__".join(part for part in path.resolve().parts if part not in {"/", ""})
    return raw.replace("/", "__").replace("\\", "__") or "workspace"


def _secretish(relative: str) -> bool:
    normalized = relative.lower()
    return any(part in normalized for part in SECRET_NAME_PARTS)


def _paths_from_git(root: Path, ignored: bool = False) -> list[str]:
    args = ["ls-files", "--others"]
    if ignored:
        args += ["-i", "--exclude-standard"]
    else:
        args += ["--exclude-standard"]
    proc = _git(root, *args, "-z")
    return [item for item in _text(proc.stdout).split("\x00") if item]


def _archive_paths(root: Path, paths: list[str], target: Path) -> list[str]:
    excluded: list[str] = []
    with tarfile.open(target, "w") as tf:
        for relative in paths:
            source = root / relative
            if _secretish(relative):
                excluded.append(relative)
                continue
            if not source.exists() and not source.is_symlink():
                continue
            tf.add(source, arcname=relative, recursive=True)
    return excluded


def _safe_extract(tar_path: Path, root: Path) -> None:
    with tarfile.open(tar_path, "r") as tf:
        root_resolved = root.resolve()
        for member in tf.getmembers():
            destination = (root / member.name).resolve()
            if destination != root_resolved and root_resolved not in destination.parents:
                raise RuntimeError(f"unsafe archive member: {member.name}")
        tf.extractall(root, filter="data")


def _run_optional(command: list[str], timeout: float = 8.0) -> str | None:
    try:
        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    output = proc.stdout.strip()
    return output[:20000] if output else ""


def host_profile() -> dict[str, Any]:
    commands = [
        "git", "python3", "node", "npm", "pnpm", "yarn", "cargo", "rustc",
        "go", "nix", "mise", "devbox", "flox", "docker", "podman",
        "devcontainer", "uv", "poetry", "bazel", "pants",
    ]
    versions: dict[str, str] = {}
    for command in commands:
        if shutil.which(command):
            output = _run_optional([command, "--version"])
            if output is not None:
                versions[command] = output

    env_names = sorted(os.environ)
    systemd = _run_optional(["systemctl", "--user", "list-units", "--type=service", "--all", "--no-legend"])
    ports = _run_optional(["ss", "-ltn"])
    processes = _run_optional(["ps", "-eo", "pid=,comm=,args="])
    distro = None
    try:
        distro = Path("/etc/os-release").read_text(encoding="utf-8", errors="replace")[:12000]
    except OSError:
        pass

    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "os_release": distro,
        "tool_versions": versions,
        "environment_variable_names": env_names,
        "user_systemd_services": systemd,
        "listening_tcp": ports,
        "process_table": processes,
    }


def _artifact(root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(root)),
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def create_capsule(
    repositories: Iterable[str | Path],
    output: str | Path,
    *,
    include_ignored: bool = False,
) -> Path:
    repo_roots = [Path(value).expanduser().resolve() for value in repositories]
    capsule = Path(output).expanduser().resolve()
    capsule.mkdir(parents=True, exist_ok=True)
    repos_dir = capsule / "repositories"
    repos_dir.mkdir(exist_ok=True)

    manifest: dict[str, Any] = {
        "schema_version": CAPSULE_SCHEMA,
        "workspace_schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": host_profile(),
        "include_ignored": include_ignored,
        "repositories": [],
    }

    for root in repo_roots:
        _git(root, "rev-parse", "--git-dir")
        slug = _safe_name(root)
        target = repos_dir / slug
        target.mkdir(parents=True, exist_ok=True)

        origin = _git(root, "config", "--get", "remote.origin.url", check=False)
        origin_url = _text(origin.stdout).strip() if origin.returncode == 0 else None
        head = _text(_git(root, "rev-parse", "HEAD").stdout).strip()
        branch = _text(_git(root, "branch", "--show-current").stdout).strip() or None
        status = _text(_git(root, "status", "--porcelain=v2", "--branch", "--untracked-files=all").stdout)
        refs_raw = _text(
            _git(root, "for-each-ref", "--format=%(refname)\\t%(objectname)\\t%(symref)").stdout
        )
        refs = []
        for line in refs_raw.splitlines():
            parts = line.split("\t", 2)
            if len(parts) == 3:
                refs.append({"ref": parts[0], "object": parts[1], "symref": parts[2] or None})

        bundle = target / "git.bundle"
        _git(root, "bundle", "create", str(bundle), "--all")

        working_patch = target / "working-tree.patch"
        working_patch.write_bytes(_git(root, "diff", "--binary", "--no-ext-diff").stdout)
        staged_patch = target / "staged.patch"
        staged_patch.write_bytes(_git(root, "diff", "--cached", "--binary", "--no-ext-diff").stdout)

        index_path = Path(_text(_git(root, "rev-parse", "--git-path", "index").stdout).strip())
        if not index_path.is_absolute():
            index_path = (root / index_path).resolve()
        index_artifact = None
        if index_path.exists():
            copied_index = target / "git-index"
            shutil.copy2(index_path, copied_index)
            index_artifact = _artifact(capsule, copied_index)

        untracked_paths = _paths_from_git(root, ignored=False)
        untracked_tar = target / "untracked.tar"
        excluded_untracked = _archive_paths(root, untracked_paths, untracked_tar)

        ignored_tar = None
        excluded_ignored: list[str] = []
        ignored_paths: list[str] = []
        if include_ignored:
            ignored_paths = _paths_from_git(root, ignored=True)
            ignored_tar = target / "ignored.tar"
            excluded_ignored = _archive_paths(root, ignored_paths, ignored_tar)

        submodules = _run_optional(["git", "-C", str(root), "submodule", "status", "--recursive"])
        split_index = _text(_git(root, "config", "--get", "core.splitIndex", check=False).stdout).strip().lower() in {"true", "yes", "on", "1"}

        repo_manifest = {
            "path": str(root),
            "origin_url": origin_url,
            "branch": branch,
            "head": head,
            "git_status_porcelain_v2": status[:50000],
            "refs": refs,
            "submodules_status": submodules,
            "split_index": split_index,
            "untracked_paths": untracked_paths,
            "ignored_paths": ignored_paths if include_ignored else [],
            "excluded_secret_like_untracked": excluded_untracked,
            "excluded_secret_like_ignored": excluded_ignored,
            "artifacts": {
                "git_bundle": _artifact(capsule, bundle),
                "working_tree_patch": _artifact(capsule, working_patch),
                "staged_patch": _artifact(capsule, staged_patch),
                "untracked_tar": _artifact(capsule, untracked_tar),
                "ignored_tar": _artifact(capsule, ignored_tar) if ignored_tar else None,
                "git_index": index_artifact,
            },
            "limitations": [
                "working-tree filesystem state outside tracked/untracked/ignored Git paths is not captured",
                "environment variable values are never captured",
                "Git credentials and secret-like files are not captured",
                "submodule local worktree changes are not recursively captured",
                "process memory and kernel state are not captured",
            ],
        }
        manifest["repositories"].append(repo_manifest)

    manifest["artifacts"] = []
    for path in capsule.rglob("*"):
        if path.is_file() and path.name != "manifest.json":
            manifest["artifacts"].append(_artifact(capsule, path))

    manifest_path = capsule / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return capsule


def restore_capsule(capsule: str | Path, destination: str | Path) -> list[Path]:
    capsule_path = Path(capsule).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    manifest = json.loads((capsule_path / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != CAPSULE_SCHEMA:
        raise ValueError("unsupported workspace capsule schema")

    restored: list[Path] = []
    for repo_manifest in manifest.get("repositories", []):
        slug = _safe_name(Path(repo_manifest["path"]))
        source = capsule_path / "repositories" / slug
        repo_dest = destination / slug
        repo_dest.parent.mkdir(parents=True, exist_ok=True)

        if repo_dest.exists():
            raise FileExistsError(f"restore target already exists: {repo_dest}")

        subprocess.run(["git", "clone", str(source / "git.bundle"), str(repo_dest)], check=True, timeout=60)

        staged = source / "staged.patch"
        if staged.stat().st_size:
            subprocess.run(["git", "-C", str(repo_dest), "apply", "--index", "--binary", str(staged)], check=True, timeout=30)

        working = source / "working-tree.patch"
        if working.stat().st_size:
            subprocess.run(["git", "-C", str(repo_dest), "apply", "--binary", str(working)], check=True, timeout=30)

        _safe_extract(source / "untracked.tar", repo_dest)
        ignored = source / "ignored.tar"
        if ignored.exists():
            _safe_extract(ignored, repo_dest)

        if repo_manifest.get("artifacts", {}).get("git_index") and not repo_manifest.get("split_index"):
            index_src = source / "git-index"
            index_dst = Path(_text(_git(repo_dest, "rev-parse", "--git-path", "index").stdout).strip())
            if not index_dst.is_absolute():
                index_dst = (repo_dest / index_dst).resolve()
            shutil.copy2(index_src, index_dst)
            _git(repo_dest, "update-index", "--refresh", check=False)

        for ref in repo_manifest.get("refs", []):
            name = ref.get("ref")
            obj = ref.get("object")
            if not name or not obj or name == "HEAD":
                continue
            if name == "refs/stash":
                _git(repo_dest, "update-ref", name, obj, check=False)

        restored.append(repo_dest)

    return restored
