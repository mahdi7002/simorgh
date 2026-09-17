from __future__ import annotations

import hashlib
from pathlib import Path

from core.hardware import HardwareProfile, classify
from core.model_manager import register_local_model, sha256_file


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
