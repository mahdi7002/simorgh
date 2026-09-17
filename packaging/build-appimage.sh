#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST="${SIMORGH_DIST_DIR:-$ROOT/dist}"
APPDIR="$DIST/AppDir"
OUT="$DIST/SIMORGH-x86_64.AppImage"
PY_RELEASE="20260807"
PY_VERSION="3.13.15"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
APPIMAGETOOL_SHA256="a6d71e2b6cd66f8e8d16c37ad164658985e0cf5fcaa950c90a482890cb9d13e0"
WORK="$DIST/.work"

rm -rf "$APPDIR" "$WORK" "$OUT"
mkdir -p "$APPDIR/usr/share/simorgh" "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps" "$WORK"

if [ ! -f "$ROOT/data/simorgh_full.db" ]; then
    echo "missing data/simorgh_full.db" >&2
    exit 1
fi
POINTER_HEADER='version https://git-lfs.github.com/spec/v1'
if head -c "${#POINTER_HEADER}" "$ROOT/data/simorgh_full.db" | grep -qF "$POINTER_HEADER"; then
    echo "data/simorgh_full.db is still a Git LFS pointer; run git lfs pull first" >&2
    exit 1
fi

# Bundle only what the end user needs at runtime. Mutable state never lives here.
cp "$ROOT/main.py" "$ROOT/requirements.txt" "$ROOT/LICENSE" "$APPDIR/usr/share/simorgh/"
for directory in core agents app dashboard models; do
    if [ -d "$ROOT/$directory" ]; then
        cp -a "$ROOT/$directory" "$APPDIR/usr/share/simorgh/"
    fi
done
mkdir -p "$APPDIR/usr/share/simorgh/data"
cp -a "$ROOT/data/." "$APPDIR/usr/share/simorgh/data/"
rm -rf "$APPDIR/usr/share/simorgh/data/reflection_proposals" "$APPDIR/usr/share/simorgh/data/snapshots"
cp "$ROOT/packaging/AppRun" "$APPDIR/AppRun"
cp "$ROOT/packaging/simorgh.desktop" "$APPDIR/usr/share/applications/simorgh.desktop"
cp "$ROOT/packaging/simorgh.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/simorgh.svg"
cp "$ROOT/packaging/simorgh.svg" "$APPDIR/simorgh.svg"
chmod +x "$APPDIR/AppRun"

# The standalone CPython release is immutable and carries its own SHA-256 in the release API.
PY_JSON="$(curl -fsSL --retry 3 --connect-timeout 10 "https://api.github.com/repos/astral-sh/python-build-standalone/releases/tags/${PY_RELEASE}")"
export PY_JSON PY_VERSION
read -r PY_URL PY_SHA <<EOF
$(python3 - <<'PY'
import json, os
payload=json.loads(os.environ['PY_JSON'])
version=os.environ['PY_VERSION']
needle=f'cpython-{version}+'
for asset in payload.get('assets', []):
    name=asset.get('name','')
    if name.startswith(needle) and name.endswith('-x86_64-unknown-linux-gnu-install_only.tar.gz'):
        print(asset['browser_download_url'], asset['digest'].split(':',1)[-1])
        break
else:
    raise SystemExit('CPython standalone x86_64 asset not found')
PY
)
EOF

PY_ARCHIVE="$WORK/cpython.tar.gz"
curl -fsSL --retry 3 --connect-timeout 10 "$PY_URL" -o "$PY_ARCHIVE"
printf '%s  %s\n' "$PY_SHA" "$PY_ARCHIVE" | sha256sum -c -
mkdir -p "$APPDIR/usr/lib/cpython"
tar -xzf "$PY_ARCHIVE" -C "$APPDIR/usr/lib/cpython" --strip-components=1
BUNDLE_PY="$APPDIR/usr/lib/cpython/bin/python3"
[ -x "$BUNDLE_PY" ]

# Put Python wheels in a deterministic private target. This avoids relying on host Python at runtime.
SITE="$APPDIR/usr/share/simorgh/.python"
mkdir -p "$SITE"
"$BUNDLE_PY" -m pip --version >/dev/null 2>&1 || "$BUNDLE_PY" -m ensurepip --upgrade
"$BUNDLE_PY" -m pip install --disable-pip-version-check --no-cache-dir --target "$SITE" -r "$ROOT/requirements.txt"

export PYTHONPATH="$SITE"
"$BUNDLE_PY" - <<'PY'
import fastapi, pydantic, uvicorn, requests, psutil
import main
print('SIMORGH_APPIMAGE_IMPORT_OK')
PY

# appimagetool is itself distributed as an AppImage. Pin the downloaded binary by SHA-256.
APPIMAGETOOL="$WORK/appimagetool-x86_64.AppImage"
curl -fsSL --retry 3 --connect-timeout 10 "$APPIMAGETOOL_URL" -o "$APPIMAGETOOL"
printf '%s  %s\n' "$APPIMAGETOOL_SHA256" "$APPIMAGETOOL" | sha256sum -c -
chmod +x "$APPIMAGETOOL"

VERSION="${SIMORGH_VERSION:-$(git -C "$ROOT" describe --tags --always --dirty 2>/dev/null || echo 0.1.0)}"
export VERSION
sed -i "s/^X-AppImage-Version=.*/X-AppImage-Version=${VERSION}/" "$APPDIR/usr/share/applications/simorgh.desktop"

# Build without FUSE requirements on the CI host.
APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" "$APPDIR" "$OUT"
chmod +x "$OUT"

echo "APPIMAGE=$OUT"
sha256sum "$OUT"
