from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_appimage_scripts_have_valid_shell_syntax():
    for relative in ("packaging/AppRun", "packaging/build-appimage.sh"):
        result = subprocess.run(
            ["bash", "-n", str(ROOT / relative)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{relative}: {result.stderr}"


def test_appimage_manifest_is_desktop_launchable():
    desktop = (ROOT / "packaging" / "simorgh.desktop").read_text(encoding="utf-8")
    assert "Type=Application" in desktop
    assert "Name=SIMORGH | سیمرغ" in desktop
    assert "Exec=AppRun" in desktop
    assert "Terminal=false" in desktop
    assert "Icon=simorgh" in desktop


def test_appimage_builder_pins_external_build_inputs():
    script = (ROOT / "packaging" / "build-appimage.sh").read_text(encoding="utf-8")
    assert 'PY_RELEASE="20260807"' in script
    assert 'PY_VERSION="3.13.15"' in script
    assert 'APPIMAGETOOL_SHA256="a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0"' in script
    assert 'sha256sum -c -' in script


def test_appimage_workflow_checks_lfs_database():
    workflow = (ROOT / ".github" / "workflows" / "build-appimage.yml").read_text(encoding="utf-8")
    assert "lfs: true" in workflow
    assert "data/simorgh_full.db" in workflow
    assert "PRAGMA integrity_check" in workflow
