from __future__ import annotations

import json
from pathlib import Path

from core import local_backend


def _fake_uname(machine: str):
    class Uname:
        pass

    value = Uname()
    value.machine = machine
    return value


def test_select_release_asset_prefers_stable_release_with_matching_cpu_asset(monkeypatch):
    monkeypatch.setattr(local_backend.os, "uname", lambda: _fake_uname("x86_64"))
    releases = [
        {
            "tag_name": "b-new",
            "prerelease": True,
            "assets": [
                {
                    "name": "llama-b-new-bin-ubuntu-x64.tar.gz",
                    "digest": "sha256:" + "1" * 64,
                    "browser_download_url": "https://example.invalid/new.tar.gz",
                }
            ],
        },
        {
            "tag_name": "v-stable",
            "prerelease": False,
            "assets": [
                {
                    "name": "llama-v-stable-bin-ubuntu-x64.tar.gz",
                    "digest": "sha256:" + "2" * 64,
                    "browser_download_url": "https://example.invalid/stable.tar.gz",
                }
            ],
        },
    ]

    selected = local_backend._select_release_asset(releases)

    assert selected["release_tag"] == "v-stable"
    assert selected["release_prerelease"] is False
    assert selected["name"].endswith("ubuntu-x64.tar.gz")


def test_select_release_asset_falls_back_when_stable_release_has_no_binary(monkeypatch):
    monkeypatch.setattr(local_backend.os, "uname", lambda: _fake_uname("x86_64"))
    releases = [
        {
            "tag_name": "v0.4.1",
            "prerelease": False,
            "assets": [
                {
                    "name": "nightly-tag.txt",
                    "digest": "sha256:" + "3" * 64,
                    "browser_download_url": "https://example.invalid/nightly-tag.txt",
                }
            ],
        },
        {
            "tag_name": "b-nightly",
            "prerelease": True,
            "assets": [
                {
                    "name": "llama-b-nightly-bin-ubuntu-x64.tar.gz",
                    "digest": "sha256:" + "4" * 64,
                    "browser_download_url": "https://example.invalid/nightly.tar.gz",
                }
            ],
        },
    ]

    selected = local_backend._select_release_asset(releases)

    assert selected["release_tag"] == "b-nightly"
    assert selected["release_prerelease"] is True


def test_start_backend_does_not_reuse_unmanaged_backend(monkeypatch, tmp_path):
    model = tmp_path / "qwen.gguf"
    model.write_bytes(b"model")

    binary = tmp_path / "llama-server"
    binary.write_bytes(b"binary")
    binary.chmod(0o755)

    pid_file = tmp_path / "llama-server.pid"
    meta_file = tmp_path / "llama-server.json"
    log_file = tmp_path / "llama-server.log"

    monkeypatch.setattr(local_backend, "BACKEND_PID_FILE", pid_file)
    monkeypatch.setattr(local_backend, "BACKEND_META_FILE", meta_file)
    monkeypatch.setattr(local_backend, "BACKEND_LOG_FILE", log_file)
    monkeypatch.setattr(local_backend.os, "environ", dict(local_backend.os.environ))
    monkeypatch.setattr(local_backend, "ensure_user_dirs", lambda: None)
    monkeypatch.setattr(
        local_backend,
        "ensure_llama_server",
        lambda: {"binary": str(binary), "downloaded": False, "verified": True},
    )

    existing = {
        "endpoint_up": True,
        "managed_pid": None,
        "managed_model": None,
        "loaded_models": ["gemma-3-4b-it-qat-Q4_0.gguf"],
    }
    ready = {
        "endpoint_up": True,
        "managed_pid": 12345,
        "managed_model": str(model),
        "loaded_models": [model.name],
    }
    states = iter([existing, ready])
    monkeypatch.setattr(local_backend, "discover_backend", lambda: next(states))
    monkeypatch.setattr(local_backend, "save_config", lambda _: None)
    monkeypatch.setattr(local_backend, "_url_ok", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(local_backend.time, "sleep", lambda *_args, **_kwargs: None)

    class FakeSocket:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def bind(self, address):
            if address[1] == 8080:
                raise OSError("occupied")
            return None

    monkeypatch.setattr(local_backend.socket, "socket", lambda: FakeSocket())

    started = {}

    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return None

    def fake_popen(args, **kwargs):
        started["args"] = args
        started["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(local_backend.subprocess, "Popen", fake_popen)

    result = local_backend.start_backend(model, preferred_port=8080)

    assert result["managed_model"] == str(model)
    assert started["args"][0] == str(binary)
    assert started["args"][1:3] == ["--model", str(model)]
    assert started["args"][started["args"].index("--port") + 1] == "8081"
    assert pid_file.read_text(encoding="utf-8") == "12345"
    metadata = json.loads(meta_file.read_text(encoding="utf-8"))
    assert metadata["model"] == str(model)
