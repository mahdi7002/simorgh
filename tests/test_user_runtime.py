from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from core.hardware import HardwareProfile, classify
from core.model_manager import install_model, load_catalog, register_local_model, sha256_file


def test_hardware_classification_is_conservative():
    assert classify(4.0, 4, None) == "small"
    assert classify(8.0, 8, None) == "medium"
    assert classify(32.0, 16, 12.0) == "large"


def test_hardware_profile_is_json_ready():
    profile = HardwareProfile(
        architecture="x86_64",
        os_name="Linux",
        kernel="test",
        cpu_model="test-cpu",
        cpu_cores=4,
        cpu_threads=8,
        cpu_mhz=3200.0,
        ram_gb=8.0,
        disk_free_gb=20.0,
        gpu=None,
        gpu_vram_gb=None,
        tier="medium",
    )
    data = profile.to_dict()
    assert data["architecture"] == "x86_64"
    assert data["tier"] == "medium"


def test_register_local_model_records_sha256(tmp_path: Path):
    model = tmp_path / "toy.gguf"
    payload = b"SIMORGH-TEST-MODEL"
    model.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()

    metadata = register_local_model(model, model_id="toy", source="test")

    assert metadata["verified"] is True
    assert metadata["sha256"] == expected
    assert sha256_file(model) == expected
    sidecar = Path(str(model) + ".simorgh.json")
    assert sidecar.is_file()


def test_model_registration_never_marks_missing_file_verified(tmp_path: Path):
    missing = tmp_path / "missing.gguf"
    try:
        register_local_model(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing model must not be registered")


def test_model_catalog_has_pinned_integrity_metadata():
    models = load_catalog()
    assert models
    for model in models:
        assert len(model["sha256"]) == 64
        assert model["download_url"].startswith("https://")
        assert model["metadata_url"].startswith("https://")
        assert model["license"] not in {"UNKNOWN", ""}


def test_model_install_refuses_incompatible_hardware(monkeypatch, tmp_path: Path):
    from core import model_manager

    fake_model = {
        "id": "tiny-test",
        "filename": "tiny.gguf",
        "download_url": "https://example.invalid/tiny.gguf",
        "sha256": "a" * 64,
        "license": "test",
        "min_ram_gb": 16,
        "min_disk_gb": 1,
        "min_vram_gb": 0,
    }
    profile = HardwareProfile(
        architecture="x86_64", os_name="Linux", kernel="test", cpu_model="test",
        cpu_cores=2, cpu_threads=4, cpu_mhz=None, ram_gb=8, disk_free_gb=20,
        gpu=None, gpu_vram_gb=None, tier="small",
    )
    monkeypatch.setattr(model_manager, "load_catalog", lambda: [fake_model])
    monkeypatch.setattr(model_manager, "probe", lambda: profile)
    try:
        install_model("tiny-test", target_dir=tmp_path)
    except RuntimeError as exc:
        assert "not compatible" in str(exc)
    else:
        raise AssertionError("incompatible hardware must block model download")


def test_database_first_chat_fallback(monkeypatch):
    from core import chat

    monkeypatch.setattr(chat, "generate", lambda *args, **kwargs: None)
    from core import database_answer
    monkeypatch.setattr(database_answer, "get_quran_wisdom", lambda *args, **kwargs: [])
    monkeypatch.setattr(database_answer, "get_poetic_wisdom", lambda *args, **kwargs: [
        {"poet": "آزمون", "title": "تست", "snippet": "پاسخ محلی"}
    ])
    monkeypatch.setattr(database_answer, "get_book_wisdom", lambda *args, **kwargs: [])

    answer = chat.ask("آزمون")
    assert "پایگاه دانش محلی" in answer
    assert "پاسخ محلی" in answer


def test_root_serves_user_app_and_bootstrap(monkeypatch):
    from core import bootstrap_api
    from main import app

    profile = HardwareProfile(
        architecture="x86_64", os_name="Linux", kernel="test", cpu_model="test",
        cpu_cores=2, cpu_threads=4, cpu_mhz=None, ram_gb=8, disk_free_gb=20,
        gpu=None, gpu_vram_gb=None, tier="small",
    )
    monkeypatch.setattr(bootstrap_api, "probe", lambda: profile)
    monkeypatch.setattr(bootstrap_api, "recommend_models", lambda _profile: [])
    monkeypatch.setattr(bootstrap_api, "installed_models", lambda: [])
    monkeypatch.setattr(bootstrap_api, "discover_backend", lambda: {"ready": False})
    monkeypatch.setattr(bootstrap_api, "runtime_snapshot", lambda: {"configured": True})

    client = TestClient(app)
    root = client.get("/")
    bootstrap = client.get("/api/bootstrap")

    assert root.status_code == 200
    assert "SIMORGH" in root.text
    assert bootstrap.status_code == 200
    assert bootstrap.json()["knowledge"]["database_first"] is True
    assert bootstrap.json()["knowledge"]["requires_model"] is False


def test_install_script_has_valid_shell_syntax():
    result = subprocess.run(["bash", "-n", "install.sh"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_catalog_is_valid_json():
    payload = json.loads(Path("models/catalog.json").read_text(encoding="utf-8"))
    assert isinstance(payload["models"], list)
    assert payload["policy"]["download_default"] is False
