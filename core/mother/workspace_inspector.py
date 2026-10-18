from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from typing import Any, Iterable


SCHEMA_VERSION = "SIMORGH_MOTHER_WORKSPACE_V1"

# Presence-only markers keep the five-minute Mother loop cheap. Heavy
# dependency/process/system inspection belongs to WorkspaceCapsule.
CONTRACT_MARKERS: tuple[tuple[str, str], ...] = (
    (".devcontainer/devcontainer.json", "devcontainer"),
    (".devcontainer.json", "devcontainer"),
    ("flake.nix", "nix"),
    ("flake.lock", "nix-lock"),
    ("mise.toml", "mise"),
    (".mise.toml", "mise"),
    ("devbox.json", "devbox"),
    ("devbox.lock", "devbox-lock"),
    ("manifest.toml", "flox"),
    ("manifest.lock", "flox-lock"),
    ("Dockerfile", "docker"),
    ("compose.yaml", "compose"),
    ("compose.yml", "compose"),
    ("docker-compose.yml", "compose"),
    ("docker-compose.yaml", "compose"),
    ("pyproject.toml", "python-pyproject"),
    ("uv.lock", "uv"),
    ("poetry.lock", "poetry"),
    ("requirements.txt", "python-requirements"),
    ("package.json", "node"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm-lock"),
    ("Cargo.toml", "rust"),
    ("Cargo.lock", "cargo-lock"),
    ("go.mod", "go"),
    ("go.sum", "go-lock"),
    ("WORKSPACE", "bazel"),
    ("WORKSPACE.bazel", "bazel"),
    ("BUILD.bazel", "bazel"),
    ("pants.toml", "pants"),
)

TOOL_HINTS = {
    "devcontainer": "devcontainer",
    "nix": "nix",
    "mise": "mise",
    "devbox": "devbox",
    "flox": "flox",
    "docker": "docker",
    "compose": "docker",
    "python-pyproject": "python3",
    "python-requirements": "python3",
    "uv": "uv",
    "poetry": "poetry",
    "node": "node",
    "npm-lock": "npm",
    "pnpm": "pnpm",
    "yarn": "yarn",
    "rust": "cargo",
    "go": "go",
    "bazel": "bazel",
    "pants": "pants",
}


class WorkspaceInspector:
    """Fast, read-only workspace contract inspector for Mother."""

    @staticmethod
    def _resolved(paths: Iterable[str | Path]) -> list[Path]:
        result: list[Path] = []
        seen: set[Path] = set()
        for value in paths:
            path = Path(value).expanduser().resolve()
            if path in seen:
                continue
            result.append(path)
            seen.add(path)
        return result

    @staticmethod
    def _repo_contract(root: Path) -> dict[str, Any]:
        markers: list[str] = []
        contracts: set[str] = set()
        available_tools: set[str] = set()

        for relative, kind in CONTRACT_MARKERS:
            if (root / relative).exists():
                markers.append(relative)
                if kind.endswith("-lock"):
                    contracts.add(kind[:-5])
                else:
                    contracts.add(kind)
                tool = TOOL_HINTS.get(kind)
                if tool and which(tool):
                    available_tools.add(tool)

        executable_candidates = []
        for relative in (
            "Makefile",
            "justfile",
            "Taskfile.yml",
            "Taskfile.yaml",
            "package.json",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
        ):
            if (root / relative).exists():
                executable_candidates.append(relative)

        return {
            "marker_files": sorted(markers),
            "contracts": sorted(contracts),
            "available_host_tools": sorted(available_tools),
            "execution_entrypoints": executable_candidates,
        }

    def inspect(
        self,
        repositories: Iterable[str | Path],
        *,
        git_states: Iterable[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        roots = self._resolved(repositories)
        states_by_path = {
            str(state.get("repository")): state
            for state in (git_states or [])
            if state.get("repository")
        }

        repo_rows: list[dict[str, Any]] = []
        for root in roots:
            git = states_by_path.get(str(root))
            repo_rows.append(
                {
                    "path": str(root),
                    "exists": root.exists(),
                    "is_directory": root.is_dir(),
                    "git_status": git.get("status") if git else "NOT_OBSERVED",
                    "sync_state": git.get("sync_state") if git else None,
                    "contract": self._repo_contract(root) if root.exists() else {
                        "marker_files": [],
                        "contracts": [],
                        "available_host_tools": [],
                        "execution_entrypoints": [],
                    },
                }
            )

        return {
            "schema_version": SCHEMA_VERSION,
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "repository_count": len(repo_rows),
            "repositories": repo_rows,
        }
