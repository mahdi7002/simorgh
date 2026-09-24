"""Local OpenAI-compatible inference backend discovery and lifecycle."""
from __future__ import annotations

import hashlib
import json
import os
import re
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

def _sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()

def _infer_release_tag(path: Path) -> str | None:
    for parent in (path.parent, *path.parents):
        match = re.fullmatch(r"llama-(b\d+|v\d+(?:\.\d+){1,3})", parent.name)
        if match:
            return match.group(1)
    return None

def _binary_provenance(path: str) -> dict[str, Any]:
    binary = Path(path).resolve()
    result: dict[str, Any] = {
        "binary_sha256": _sha256_file(binary),
        "release_tag": _infer_release_tag(binary),
        "release_prerelease": False,
        "provenance_verified": False,
    }
    for parent in (binary.parent, *binary.parents):
        metadata_path = parent / "simorgh-backend.json"
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if metadata.get("binary_sha256") == result["binary_sha256"]:
            result["release_tag"] = metadata.get("release_tag") or result["release_tag"]
            result["release_prerelease"] = bool(metadata.get("release_prerelease"))
            result["provenance_verified"] = bool(metadata.get("provenance_verified"))
            result["asset"] = metadata.get("asset")
            result["archive_sha256"] = metadata.get("archive_sha256")
        break
    if isinstance(result.get("release_tag"), str) and result["release_tag"].startswith("b"):
        result["release_prerelease"] = True
    return result

def _process_cmdline(pid: int) -> list[str] | None:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return None
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]

def _cleanup_managed_state() -> None:
    BACKEND_PID_FILE.unlink(missing_ok=True)
    BACKEND_META_FILE.unlink(missing_ok=True)

def _model_id_matches(model_id: str, model: Path) -> bool:
    if not isinstance(model_id, str) or not model_id:
        return False
    try:
        candidate = Path(model_id).expanduser()
        if candidate.is_absolute() and candidate.resolve() == model:
            return True
    except OSError:
        pass
    return Path(model_id).name == model.name

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
        return {"binary": binary, "downloaded": False, "verified": True, **_binary_provenance(binary)}

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
        binary_sha256 = _sha256_file(found)
        release_tag = asset.get("release_tag")
        release_prerelease = bool(asset.get("release_prerelease"))
        (extract_dir / "simorgh-backend.json").write_text(
            json.dumps(
                {
                    "binary_sha256": binary_sha256,
                    "release_tag": release_tag,
                    "release_prerelease": release_prerelease,
                    "asset": asset.get("name"),
                    "archive_sha256": expected,
                    "provenance_verified": True,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        keep_extract = True
        return {
            "binary": str(found),
            "downloaded": True,
            "verified": True,
            "sha256": expected,
            "binary_sha256": binary_sha256,
            "asset": asset.get("name"),
            "release_tag": asset.get("release_tag"),
            "release_prerelease": asset.get("release_prerelease"),
        }
    finally:
        archive.unlink(missing_ok=True)
        if not keep_extract:
            shutil.rmtree(extract_dir, ignore_errors=True)


def _managed_pid() -> int | None:
    metadata: dict[str, Any] = {}
    try:
        metadata = json.loads(BACKEND_META_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        metadata = {}

    candidate_pids: list[int] = []
    try:
        pid = int(BACKEND_PID_FILE.read_text(encoding="utf-8").strip())
        candidate_pids.append(pid)
    except (OSError, ValueError):
        pass

    metadata_pid = metadata.get("pid")
    if isinstance(metadata_pid, int) and metadata_pid > 0 and metadata_pid not in candidate_pids:
        candidate_pids.append(metadata_pid)

    for pid in candidate_pids:
        try:
            os.kill(pid, 0)
        except OSError:
            continue

        cmdline = _process_cmdline(pid)
        if not cmdline or Path(cmdline[0]).name != "llama-server":
            continue

        expected_binary = metadata.get("binary")
        if isinstance(expected_binary, str) and expected_binary:
            try:
                if Path(cmdline[0]).resolve() != Path(expected_binary).expanduser().resolve():
                    continue
            except OSError:
                continue

        expected_model = metadata.get("model")
        if isinstance(expected_model, str) and expected_model:
            try:
                model_index = cmdline.index("--model")
                if Path(cmdline[model_index + 1]).expanduser().resolve() != Path(expected_model).expanduser().resolve():
                    continue
            except (ValueError, IndexError, OSError):
                continue

        expected_port = metadata.get("port")
        if isinstance(expected_port, int):
            try:
                port_index = cmdline.index("--port")
                if int(cmdline[port_index + 1]) != expected_port:
                    continue
            except (ValueError, IndexError):
                continue

        # Repair a stale PID file when metadata identifies the live managed
        # process. This prevents a previous process PID from orphaning a
        # healthy llama-server instance.
        if BACKEND_PID_FILE.read_text(encoding="utf-8").strip() != str(pid):
            BACKEND_PID_FILE.write_text(str(pid), encoding="utf-8")
        return pid

    _cleanup_managed_state()
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
    loaded_models = existing.get("loaded_models") or []
    if not managed_pid or not isinstance(managed_model, str) or not managed_model:
        return False
    try:
        metadata_match = Path(managed_model).expanduser().resolve() == model
    except OSError:
        metadata_match = False
    return metadata_match and any(_model_id_matches(model_id, model) for model_id in loaded_models)


def start_backend(model_path: str | os.PathLike[str], *, preferred_port: int = 8080) -> dict[str, Any]:
    model = Path(model_path).expanduser().resolve()
    if not model.is_file():
        raise FileNotFoundError(model)
    binary_info = ensure_llama_server()
    existing = discover_backend()
    if existing["endpoint_up"]:
        if _managed_model_matches(existing, model):
            port = existing.get("managed_port")
            if isinstance(port, int) and port > 0:
                fast_url = f"http://127.0.0.1:{port}/v1/chat/completions"
                models_url = f"http://127.0.0.1:{port}/v1/models"
                os.environ["SIMORGH_LLM_FAST_URL"] = fast_url
                os.environ["SIMORGH_LLM_FAST_MODELS_URL"] = models_url
                os.environ["SIMORGH_LLM_QUALITY_URL"] = fast_url
                os.environ["SIMORGH_LLM_QUALITY_MODELS_URL"] = models_url
                save_config(
                    {
                        "llm_fast_url": fast_url,
                        "llm_fast_models_url": models_url,
                        "llm_quality_url": fast_url,
                        "llm_quality_models_url": models_url,
                    }
                )
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
    env["SIMORGH_LLM_QUALITY_URL"] = fast_url
    env["SIMORGH_LLM_QUALITY_MODELS_URL"] = models_url
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
            payload = _models_payload(models_url, timeout=2)
            loaded_models = _model_ids(payload)
            if not any(_model_id_matches(model_id, model) for model_id in loaded_models):
                try:
                    process.terminate()
                except OSError:
                    pass
                _cleanup_managed_state()
                log.close()
                raise RuntimeError(
                    f"llama-server reported unexpected model(s): {loaded_models!r}; expected {model}"
                )
            log.close()
            os.environ["SIMORGH_LLM_FAST_URL"] = fast_url
            os.environ["SIMORGH_LLM_FAST_MODELS_URL"] = models_url
            os.environ["SIMORGH_LLM_QUALITY_URL"] = fast_url
            os.environ["SIMORGH_LLM_QUALITY_MODELS_URL"] = models_url
            save_config(
                {
                    "llm_fast_url": fast_url,
                    "llm_fast_models_url": models_url,
                    "llm_quality_url": fast_url,
                    "llm_quality_models_url": models_url,
                    "backend_pid": process.pid,
                    "backend_model": str(model),
                    "backend_binary": binary_info["binary"],
                    "backend_binary_sha256": binary_info.get("binary_sha256") or binary_info.get("sha256"),
                    "backend_binary_provenance_verified": bool(binary_info.get("provenance_verified")),
                    "backend_release": binary_info.get("release_tag"),
                    "backend_release_prerelease": binary_info.get("release_prerelease"),
                }
            )
            return discover_backend()
        time.sleep(0.25)
    try:
        process.terminate()
    except OSError:
        pass
    _cleanup_managed_state()
    log.close()
    raise RuntimeError(f"llama-server did not become ready; see {BACKEND_LOG_FILE}")


def discover_backend() -> dict[str, Any]:
    configured_fast_url = os.environ.get(
        "SIMORGH_LLM_FAST_URL",
        "http://127.0.0.1:8080/v1/chat/completions",
    )
    configured_models_url = os.environ.get(
        "SIMORGH_LLM_FAST_MODELS_URL",
        "http://127.0.0.1:8080/v1/models",
    )
    binary = _find_binary()
    pid = _managed_pid()
    meta: dict[str, Any] = {}
    try:
        meta = json.loads(BACKEND_META_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass

    managed_port = meta.get("port") if pid is not None else None
    if isinstance(managed_port, int) and managed_port > 0:
        # The managed process metadata is authoritative for the process we
        # discovered. Do not let a stale shell/runtime environment point
        # discovery at a different port.
        fast_url = f"http://127.0.0.1:{managed_port}/v1/chat/completions"
        models_url = f"http://127.0.0.1:{managed_port}/v1/models"
    else:
        fast_url = configured_fast_url
        models_url = configured_models_url

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
        "managed_port": managed_port,
        "loaded_models": model_ids,
        "ready": endpoint_up,
        "note": "مدل و backend دو مؤلفهٔ جدا هستند؛ سیمورغ فقط backend محلیِ مدیریت‌شدهٔ خودش را در اختیار می‌گیرد.",
    }


__all__ = ["discover_backend", "ensure_llama_server", "start_backend", "stop_managed_backend"]
