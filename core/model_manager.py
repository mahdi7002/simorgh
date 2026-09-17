"""Local model catalog, recommendation, download and integrity verification.

No model is downloaded automatically. A model becomes usable only after its
file digest has been verified and a sidecar records its provenance.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from core.hardware import HardwareProfile, probe
from core.user_runtime import RUNTIME_MODEL_DIR, ensure_user_dirs

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "models" / "catalog.json"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def load_catalog() -> list[dict[str, Any]]:
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    models = payload.get("models", []) if isinstance(payload, dict) else []
    return [m for m in models if isinstance(m, dict) and m.get("id")]


def _usable_for(profile: HardwareProfile, model: dict[str, Any]) -> bool:
    return (
        profile.ram_gb >= float(model.get("min_ram_gb", 0))
        and profile.disk_free_gb >= float(model.get("min_disk_gb", 0))
        and (
            float(model.get("min_vram_gb", 0)) <= 0
            or (profile.gpu_vram_gb is not None and profile.gpu_vram_gb >= float(model.get("min_vram_gb", 0)))
        )
    )


def recommend_models(profile: HardwareProfile | None = None) -> list[dict[str, Any]]:
    profile = profile or probe()
    results: list[dict[str, Any]] = []
    for model in load_catalog():
        item = dict(model)
        item["compatible"] = _usable_for(profile, model)
        item["recommended"] = item["compatible"] and model.get("tier") == profile.tier
        results.append(item)
    results.sort(key=lambda m: (not m["recommended"], not m["compatible"], float(m.get("min_ram_gb", 0))))
    return results


def _metadata_sha(model: dict[str, Any]) -> str | None:
    sha = str(model.get("sha256", "")).strip().lower()
    if _SHA256_RE.fullmatch(sha):
        return sha
    url = model.get("metadata_url")
    filename = model.get("filename")
    if not url or not filename:
        return None
    try:
        request = urllib.request.Request(str(url), headers={"User-Agent": "SIMORGH/1.0"})
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for sibling in payload.get("siblings", []):
            if sibling.get("rfilename") != filename:
                continue
            lfs_oid = ((sibling.get("lfs") or {}).get("oid") or "").lower()
            if _SHA256_RE.fullmatch(lfs_oid):
                return lfs_oid
            xet_sha = str(((sibling.get("xet") or {}).get("sha256") or "")).lower()
            if _SHA256_RE.fullmatch(xet_sha):
                return xet_sha
    except Exception as exc:
        logger.warning("model metadata lookup failed: %s", exc)
    return None


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".simorgh.json")


def register_local_model(
    path: str | os.PathLike[str],
    *,
    model_id: str = "imported-local-model",
    license_name: str = "UNKNOWN",
    source: str = "local file",
) -> dict[str, Any]:
    model_path = Path(path).expanduser().resolve()
    if not model_path.is_file():
        raise FileNotFoundError(model_path)
    digest = sha256_file(model_path)
    metadata = {
        "schema_version": 1,
        "model_id": model_id,
        "path": str(model_path),
        "sha256": digest,
        "format": model_path.suffix.lstrip(".") or "unknown",
        "license": license_name,
        "source": source,
        "verified": True,
    }
    _sidecar(model_path).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def install_model(
    model_id: str,
    target_dir: str | os.PathLike[str] | None = None,
    *,
    profile: HardwareProfile | None = None,
) -> dict[str, Any]:
    catalog = {m["id"]: m for m in load_catalog()}
    model = catalog.get(model_id)
    if not model:
        raise KeyError(f"unknown model: {model_id}")
    profile = profile or probe()
    if not _usable_for(profile, model):
        raise RuntimeError(
            f"model is not compatible with detected resources: tier={profile.tier}, "
            f"ram={profile.ram_gb}GB, free_disk={profile.disk_free_gb}GB"
        )
    url = str(model.get("download_url", "")).strip()
    filename = str(model.get("filename", "")).strip()
    if not url or not filename:
        raise ValueError("model catalog entry has no download URL/filename")
    expected = _metadata_sha(model)
    if not expected:
        raise RuntimeError("model integrity hash is unavailable; refusing unverified download")
    ensure_user_dirs()
    directory = Path(target_dir).expanduser().resolve() if target_dir else RUNTIME_MODEL_DIR
    directory.mkdir(parents=True, exist_ok=True)
    final_path = directory / filename
    if final_path.is_file() and sha256_file(final_path) == expected:
        return register_local_model(
            final_path,
            model_id=model_id,
            license_name=str(model.get("license", "UNKNOWN")),
            source=url,
        )

    fd, tmp_name = tempfile.mkstemp(prefix=f".{filename}.", suffix=".part", dir=directory)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "SIMORGH/1.0"})
        with urllib.request.urlopen(request, timeout=60) as response, tmp_path.open("wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        actual = sha256_file(tmp_path)
        if actual.lower() != expected.lower():
            raise RuntimeError(f"sha256 mismatch: expected {expected}, got {actual}")
        tmp_path.replace(final_path)
        return register_local_model(
            final_path,
            model_id=model_id,
            license_name=str(model.get("license", "UNKNOWN")),
            source=url,
        )
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def installed_models(directory: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    root = Path(directory).expanduser().resolve() if directory else RUNTIME_MODEL_DIR
    if not root.is_dir():
        return []
    results: list[dict[str, Any]] = []
    for path in sorted(root.iterdir()):
        if not path.is_file() or path.suffix.lower() not in {".gguf", ".onnx", ".bin"}:
            continue
        sidecar = _sidecar(path)
        item: dict[str, Any]
        try:
            item = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.is_file() else {}
        except (OSError, ValueError):
            item = {}
        item.update({"path": str(path), "filename": path.name, "verified": bool(item.get("verified"))})
        results.append(item)
    return results


__all__ = [
    "installed_models",
    "install_model",
    "load_catalog",
    "recommend_models",
    "register_local_model",
    "sha256_file",
]
