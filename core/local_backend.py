"""Local OpenAI-compatible inference backend discovery and lifecycle."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any

from core.user_runtime import DEFAULT_RUNTIME_DIR, RUNTIME_LOG_DIR, ensure_user_dirs, save_config

BACKEND_PID_FILE = DEFAULT_RUNTIME_DIR / "llama-server.pid"
BACKEND_META_FILE = DEFAULT_RUNTIME_DIR / "llama-server.json"
BACKEND_LOG_FILE = RUNTIME_LOG_DIR / "llama-server.log"
GITHUB_RELEASES = "https://api.github.com/repos/ggml-org/llama.cpp/releases"


def _url_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 500
    except Exception:
        return False


def _models_payload(url: str, timeout: float = 1.5) -> dict[str, Any] | None:
    try:
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "SIMORGH/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _model_ids(payload: dict[str, Any] | None) -> list[str]:
    if not payload:
        return []
    entries = payload.get("data") or payload.get("models") or []
    if not isinstance(entries, list):
        return []
    ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        value = entry.get("id") or entry.get("model") or entry.get("name")
        if isinstance(value, str) and value:
            ids.append(value)
    return ids


def _binary_usable(path: str) -> bool:
    try:
        result = subprocess.run(
            [path, "--version"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _find_binary() -> str | None:
    candidates = [
        shutil.which("llama-server"),
        str(Path(__file__).resolve().parents[1] / "bin" / "llama-server"),
        str(DEFAULT_RUNTIME_DIR / "bin" / "llama-server"),
    ]
    direct = next(
        (
            p for p in candidates
            if p and Path(p).is_file() and os.access(p, os.X_OK) and _binary_usable(p)
        ),
        None,
    )
    if direct:
        return direct
    runtime_bin = DEFAULT_RUNTIME_DIR / "bin"
    if runtime_bin.is_dir():
        nested = sorted(
            (
                p for p in runtime_bin.rglob("llama-server")
                if p.is_file() and os.access(p, os.X_OK) and _binary_usable(str(p))
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if nested:
            return str(nested[0])
    return None


def _free_port(start: int = 8080, end: int = 8090) -> int:
    for port in range(start, end + 1):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free local backend port in 8080-8090")


def _release_list() -> list[dict[str, Any]]:
    request = urllib.request.Request(
        GITHUB_RELEASES,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "SIMORGH/1.0"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise RuntimeError("llama.cpp releases API returned an unexpected payload")
    return [item for item in payload if isinstance(item, dict)]


def _asset_for_host(assets: list[dict[str, Any]]) -> dict[str, Any] | None:
    machine = os.uname().machine.lower() if hasattr(os, "uname") else ""
    if machine in {"x86_64", "amd64"}:
        token = "ubuntu-x64"
    elif machine in {"aarch64", "arm64"}:
        token = "ubuntu-arm64"
    elif machine in {"s390x", "s390"}:
        token = "ubuntu-s390x"
    else:
        raise RuntimeError(f"unsupported llama.cpp host architecture: {machine or 'unknown'}")
    matches = [
        asset
        for asset in assets
        if token in str(asset.get("name", ""))
        and str(asset.get("name", "")).endswith(".tar.gz")
        and "bin-" in str(asset.get("name", ""))
        and all(
            part not in str(asset.get("name", "")).lower()
            for part in ("cuda", "vulkan", "rocm", "openvino", "sycl", "hip")
        )
    ]
    return matches[0] if matches else None


def _select_release_asset(releases: list[dict[str, Any]]) -> dict[str, Any]:
    """Select the newest official CPU asset, preferring stable releases.

    Some stable releases can exist without binary assets and instead point at a
    nightly build. In that case, use the newest release with a matching CPU
    asset and preserve its prerelease status in the returned provenance.
    """
    prerelease_candidate: dict[str, Any] | None = None
    for release in releases:
        if release.get("draft"):
            continue
        asset = _asset_for_host(release.get("assets") or [])
        if asset is None:
            continue
        candidate = {
            **asset,
            "release_tag": release.get("tag_name"),
            "release_name": release.get("name"),
            "release_prerelease": bool(release.get("prerelease")),
        }
        if not candidate["release_prerelease"]:
            return candidate
        if prerelease_candidate is None:
            prerelease_candidate = candidate
    if prerelease_candidate is not None:
        return prerelease_candidate
    machine = os.uname().machine.lower() if hasattr(os, "uname") else "unknown"
    raise RuntimeError(f"no verified CPU llama.cpp binary available for ubuntu host architecture {machine}")


def ensure_llama_server() -> dict[str, Any]:
    """Ensure a verified CPU llama-server binary exists locally."""
    ensure_user_dirs()
    binary = _find_binary()
    if binary:
        return {"binary": binary, "downloaded": False, "verified": True}

    asset = _select_release_asset(_release_list())
    digest = str(asset.get("digest", ""))
    if not digest.startswith("sha256:") or len(digest.split(":", 1)[1]) != 64:
        raise RuntimeError("llama.cpp release asset has no usable SHA-256; refusing unverified backend")
    expected = digest.split(":", 1)[1].lower()
    url = str(asset.get("browser_download_url", ""))
    if not url:
        raise RuntimeError("llama.cpp release asset has no download URL")

    backend_dir = DEFAULT_RUNTIME_DIR / "bin"
    backend_dir.mkdir(parents=True, exist_ok=True)
    fd, archive_name = tempfile.mkstemp(prefix="llama-server-", suffix=".tar.gz", dir=backend_dir)
    os.close(fd)
    archive = Path(archive_name)
    extract_dir = Path(tempfile.mkdtemp(prefix="llama-bundle-", dir=backend_dir))
    keep_extract = False
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SIMORGH/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        digest_actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest_actual != expected:
            raise RuntimeError(f"llama.cpp backend SHA-256 mismatch: expected {expected}, got {digest_actual}")

        with tarfile.open(archive, "r:gz") as tar:
            root = extract_dir.resolve()
            for member in tar.getmembers():
                target = (extract_dir / member.name).resolve()
                if root not in target.parents and target != root:
                    raise RuntimeError("unsafe llama.cpp archive path")
            tar.extractall(extract_dir)

        found = next((p for p in extract_dir.rglob("llama-server") if p.is_file()), None)
        if found is None:
            raise RuntimeError("verified llama.cpp archive did not contain llama-server")
        found.chmod(found.stat().st_mode | 0o111)
        keep_extract = True
        return {
            "binary": str(found),
            "downloaded": True,
            "verified": True,
            "sha256": expected,
            "asset": asset.get("name"),
            "release_tag": asset.get("release_tag"),
            "release_prerelease": asset.get("release_prerelease"),
        }
    finally:
        archive.unlink(missing_ok=True)
        if not keep_extract:
            shutil.rmtree(extract_dir, ignore_errors=True)


def _managed_pid() -> int | None:
    try:
        pid = int(BACKEND_PID_FILE.read_text(encoding="utf-8").strip())
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError):
        BACKEND_PID_FILE.unlink(missing_ok=True)
        return None


def stop_managed_backend() -> bool:
    pid = _managed_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass
    BACKEND_PID_FILE.unlink(missing_ok=True)
    return True


def _managed_model_matches(existing: dict[str, Any], model: Path) -> bool:
    managed_pid = existing.get("managed_pid")
    managed_model = existing.get("managed_model")
    if not managed_pid or not isinstance(managed_model, str) or not managed_model:
        return False
    try:
        return Path(managed_model).expanduser().resolve() == model
    except OSError:
        return False


def start_backend(model_path: str | os.PathLike[str], *, preferred_port: int = 8080) -> dict[str, Any]:
    model = Path(model_path).expanduser().resolve()
    if not model.is_file():
        raise FileNotFoundError(model)
    binary_info = ensure_llama_server()
    existing = discover_backend()
    if existing["endpoint_up"]:
        if _managed_model_matches(existing, model):
            existing["note"] = "SIMORGH-managed local backend already serves the requested model"
            return existing
        if existing.get("managed_pid") is not None:
            stop_managed_backend()
        # An unmanaged backend is deliberately left untouched. SIMORGH starts
        # its own managed backend on a free loopback port instead of silently
        # treating another process/model as the requested model.

    ensure_user_dirs()
    port = preferred_port
    try:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))
    except OSError:
        port = _free_port()

    env = os.environ.copy()
    fast_url = f"http://127.0.0.1:{port}/v1/chat/completions"
    models_url = f"http://127.0.0.1:{port}/v1/models"
    env["SIMORGH_LLM_FAST_URL"] = fast_url
    env["SIMORGH_LLM_FAST_MODELS_URL"] = models_url
    log = BACKEND_LOG_FILE.open("ab")
    process = subprocess.Popen(
        [
            binary_info["binary"],
            "--model",
            str(model),
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--ctx-size",
            "4096",
        ],
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=env,
    )
    BACKEND_PID_FILE.write_text(str(process.pid), encoding="utf-8")
    BACKEND_META_FILE.write_text(
        json.dumps({"pid": process.pid, "model": str(model), "port": port}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    for _ in range(120):
        if process.poll() is not None:
            pid_file.unlink(missing_ok=True)
            meta_file = BACKEND_META_FILE
            meta_file.unlink(missing_ok=True)
            log.close()
            raise RuntimeError(f"llama-server exited with code {process.returncode}; see {BACKEND_LOG_FILE}")
        if _url_ok(models_url, timeout=1):
            log.close()
            os.environ["SIMORGH_LLM_FAST_URL"] = fast_url
            os.environ["SIMORGH_LLM_FAST_MODELS_URL"] = models_url
            save_config(
                {
                    "llm_fast_url": fast_url,
                    "llm_fast_models_url": models_url,
                    "backend_pid": process.pid,
                    "backend_model": str(model),
                    "backend_binary": binary_info["binary"],
                    "backend_binary_sha256": binary_info.get("sha256"),
                    "backend_release": binary_info.get("release_tag"),
                    "backend_release_prerelease": binary_info.get("release_prerelease"),
                }
            )
            return discover_backend()
        time.sleep(0.25)
    log.close()
    raise RuntimeError(f"llama-server did not become ready; see {BACKEND_LOG_FILE}")


def discover_backend() -> dict[str, Any]:
    fast_url = os.environ.get("SIMORGH_LLM_FAST_URL", "http://127.0.0.1:8080/v1/chat/completions")
    models_url = os.environ.get("SIMORGH_LLM_FAST_MODELS_URL", "http://127.0.0.1:8080/v1/models")
    binary = _find_binary()
    pid = _managed_pid()
    meta: dict[str, Any] = {}
    try:
        meta = json.loads(BACKEND_META_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    payload = _models_payload(models_url)
    model_ids = _model_ids(payload)
    endpoint_up = payload is not None
    return {
        "provider": "openai-compatible",
        "endpoint": fast_url,
        "models_endpoint": models_url,
        "endpoint_up": endpoint_up,
        "llama_server_binary": binary,
        "managed_pid": pid,
        "managed_model": meta.get("model") if pid is not None else None,
        "managed_port": meta.get("port") if pid is not None else None,
        "loaded_models": model_ids,
        "ready": endpoint_up,
        "note": "مدل و backend دو مؤلفهٔ جدا هستند؛ سیمورغ فقط backend محلیِ مدیریت‌شدهٔ خودش را در اختیار می‌گیرد.",
    }


__all__ = ["discover_backend", "ensure_llama_server", "start_backend", "stop_managed_backend"]
