from __future__ import annotations

import gc
import sqlite3
import subprocess
import sys
import textwrap
from pathlib import Path


def test_import_and_bootstrap_do_not_leak_sqlite_connections():
    """Run the real import/request path in a fresh interpreter and audit connects."""
    script = textwrap.dedent(
        r'''
        import gc
        import json
        import sqlite3
        import traceback
        import weakref

        original_connect = sqlite3.connect
        opened = []

        class TrackingConnection(sqlite3.Connection):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self._simorgh_closed = False
                self._simorgh_stack = "".join(traceback.format_stack(limit=18))
                opened.append(self)

            def close(self):
                self._simorgh_closed = True
                return super().close()

        def connect(*args, **kwargs):
            kwargs.setdefault("factory", TrackingConnection)
            return original_connect(*args, **kwargs)

        sqlite3.connect = connect

        from fastapi.testclient import TestClient
        from core import bootstrap_api
        from core.hardware import HardwareProfile
        from main import app

        profile = HardwareProfile(
            architecture="x86_64", os_name="Linux", kernel="test", cpu_model="test",
            cpu_cores=2, cpu_threads=4, cpu_mhz=None, ram_gb=8, disk_free_gb=20,
            gpu=None, gpu_vram_gb=None, tier="small",
        )
        bootstrap_api.probe = lambda: profile
        bootstrap_api.recommend_models = lambda _profile: []
        bootstrap_api.installed_models = lambda: []
        bootstrap_api.discover_backend = lambda: {"ready": False}
        bootstrap_api.runtime_snapshot = lambda: {"configured": True}

        with TestClient(app) as client:
            assert client.get("/").status_code == 200
            assert client.get("/api/bootstrap").status_code == 200

        gc.collect()
        leaks = [
            {"closed": c._simorgh_closed, "stack": c._simorgh_stack}
            for c in opened
            if not c._simorgh_closed
        ]
        print(json.dumps({"opened": len(opened), "leaks": leaks}, ensure_ascii=False))
        if leaks:
            raise SystemExit(17)
        '''
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
