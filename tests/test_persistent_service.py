from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_persistent_service_runner_has_valid_shell_syntax():
    result = subprocess.run(
        ["bash", "-n", str(ROOT / "scripts" / "simorgh-run.sh")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_installer_enables_persistent_user_service():
    installer = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "systemctl --user enable --now simorgh.service" in installer
    assert "Restart=always" in installer
    assert "loginctl enable-linger" in installer
    assert "scripts/simorgh-run.sh" in installer
    assert "systemctl --user is-active --quiet simorgh.service" in installer


def test_stop_script_stops_persistent_user_service():
    stop = (ROOT / "stop.sh").read_text(encoding="utf-8")
    assert "systemctl --user stop simorgh.service" in stop


def test_service_reference_is_not_machine_specific():
    service = (ROOT / "simorgh-core.service").read_text(encoding="utf-8")
    assert "User=mahdi" not in service
    assert "%h/simorgh/scripts/simorgh-run.sh" in service
    assert "Restart=always" in service
    assert "WantedBy=default.target" in service
