from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from shutil import which
from urllib.parse import urlparse

from .workspace_capsule import create_capsule, restore_capsule
from .workspace_inspector import WorkspaceInspector
from .project_auditor import audit_project, audit_system


def _is_url(value: str) -> bool:
    return value.startswith(("https://", "http://", "ssh://", "git@"))


def _clone_source(source: str) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
    if not _is_url(source):
        return Path(source).expanduser().resolve(), None
    temp = tempfile.TemporaryDirectory(prefix="simorgh-mother-source-")
    target = Path(temp.name) / "repo"
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", "--recurse-submodules", source, str(target)],
            check=True,
            timeout=180,
        )
    except Exception:
        temp.cleanup()
        raise
    return target, temp


def _executor(root: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    if (root / ".devcontainer/devcontainer.json").exists() or (root / ".devcontainer.json").exists():
        if which("devcontainer"):
            return "devcontainer"
    if (root / "flake.nix").exists() and which("nix"):
        return "nix"
    if (root / "mise.toml").exists() or (root / ".mise.toml").exists():
        if which("mise"):
            return "mise"
    return "direct"


def run_command(root: Path, command: list[str], executor: str = "auto") -> int:
    if not command:
        raise ValueError("no command supplied")
    mode = _executor(root, executor)
    if mode == "devcontainer":
        subprocess.run(["devcontainer", "up", "--workspace-folder", str(root)], check=True, timeout=300)
        proc = subprocess.run(["devcontainer", "exec", "--workspace-folder", str(root), *command])
    elif mode == "nix":
        proc = subprocess.run(["nix", "develop", str(root), "--command", *command], cwd=root)
    elif mode == "mise":
        proc = subprocess.run(["mise", "exec", "--", *command], cwd=root)
    elif mode == "direct":
        proc = subprocess.run(command, cwd=root)
    else:
        raise ValueError(f"unsupported executor: {mode}")
    return proc.returncode


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mother-workspace")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser("inspect")
    inspect_p.add_argument("source")

    snap_p = sub.add_parser("snapshot")
    snap_p.add_argument("sources", nargs="+")
    snap_p.add_argument("--output", required=True)
    snap_p.add_argument("--include-ignored", action="store_true")

    restore_p = sub.add_parser("restore")
    restore_p.add_argument("capsule")
    restore_p.add_argument("--destination", required=True)

    run_p = sub.add_parser("run")
    run_p.add_argument("source")
    run_p.add_argument("--executor", choices=("auto", "direct", "devcontainer", "nix", "mise"), default="auto")
    run_p.add_argument("command_args", nargs=argparse.REMAINDER)

    audit_p = sub.add_parser("audit")
    audit_p.add_argument("source")
    audit_p.add_argument("--execute", action="store_true")
    audit_p.add_argument("--timeout", type=int, default=120)

    audit_system_p = sub.add_parser("audit-system")
    audit_system_p.add_argument("roots", nargs="+", default=[str(Path.home())])
    audit_system_p.add_argument("--execute", action="store_true")
    audit_system_p.add_argument("--timeout", type=int, default=120)
    audit_system_p.add_argument("--max-projects", type=int, default=250)

    args = parser.parse_args(argv)

    if args.command == "inspect":
        root, temp = _clone_source(args.source)
        try:
            payload = WorkspaceInspector().inspect([root])
            payload["source"] = args.source
            payload["source_mode"] = "remote_clone" if temp else "local_workspace"
            payload["important_limitation"] = (
                "A repository URL exposes source state, not another developer's uncommitted files, local config, "
                "processes, credentials, or machine state. Use a Mother capsule for exact workspace recovery."
            )
            _print_json(payload)
        finally:
            if temp:
                temp.cleanup()
        return 0

    if args.command == "snapshot":
        roots: list[Path] = []
        temps: list[tempfile.TemporaryDirectory[str]] = []
        try:
            for source in args.sources:
                root, temp = _clone_source(source)
                roots.append(root)
                if temp:
                    temps.append(temp)
            capsule = create_capsule(roots, args.output, include_ignored=args.include_ignored)
            print(capsule)
            return 0
        finally:
            for temp in temps:
                temp.cleanup()

    if args.command == "restore":
        restored = restore_capsule(args.capsule, args.destination)
        for path in restored:
            print(path)
        return 0

    if args.command == "audit":
        root, temp = _clone_source(args.source)
        try:
            payload = audit_project(root, execute=args.execute, timeout=args.timeout)
            payload["source"] = args.source
            payload["source_mode"] = "remote_clone" if temp else "local_workspace"
            _print_json(payload)
            return 0 if payload.get("health") not in {"FAIL", "UNAVAILABLE"} else 1
        finally:
            if temp:
                temp.cleanup()

    if args.command == "audit-system":
        payload = audit_system(args.roots, execute=args.execute, timeout=args.timeout, max_projects=args.max_projects)
        _print_json(payload)
        return 0 if payload.get("health_counts", {}).get("FAIL", 0) == 0 else 1

    if args.command == "run":
        command_args = list(args.command_args)
        if command_args and command_args[0] == "--":
            command_args = command_args[1:]
        root, temp = _clone_source(args.source)
        try:
            mode = _executor(root, args.executor)
            print(json.dumps({"source": args.source, "workspace": str(root), "executor": mode, "command": command_args}, ensure_ascii=False, indent=2))
            if not command_args:
                print("No command executed. Supply: run <source> -- <command> [args...]")
                return 0
            return run_command(root, command_args, mode)
        finally:
            if temp:
                temp.cleanup()

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
