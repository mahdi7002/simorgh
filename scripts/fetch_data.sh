#!/usr/bin/env bash
# Downloads SIMORGH data assets from the "data" GitHub Release and verifies SHA-256.
# Env: SIMORGH_DATA_REPO (default mahdi7002/simorgh), SIMORGH_DATA_TAG (default data)
set -euo pipefail
REPO="${SIMORGH_DATA_REPO:-mahdi7002/simorgh}"
TAG="${SIMORGH_DATA_TAG:-data}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="https://github.com/${REPO}/releases/download/${TAG}"
mkdir -p "$ROOT/data"
TMP="$(mktemp -d "$ROOT/data/.fetch.XXXXXX")"; trap 'rm -rf "$TMP"' EXIT
echo "Fetching manifest from $BASE"
curl -fsSL --retry 3 "$BASE/MANIFEST.json" -o "$TMP/MANIFEST.json" || { echo "ERROR: cannot download the data manifest (release '$TAG' missing or no network)"; exit 2; }
python3 - "$TMP/MANIFEST.json" "$BASE" "$ROOT" "$TMP" <<'PY'
import gzip, hashlib, json, os, shutil, subprocess, sys
mf, base, root, tmp = sys.argv[1:5]
m = json.load(open(mf))
def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 22), b""): h.update(c)
    return h.hexdigest()
print("data version:", m.get("version"))
for e in m["files"]:
    dest = os.path.join(root, e["dest"])
    if os.path.isfile(dest) and os.path.getsize(dest) == e["bytes"] and sha(dest) == e["sha256"]:
        print("up to date:", e["dest"]); continue
    gz = os.path.join(tmp, e["gz"])
    for attempt in range(1, 21):
        rc = subprocess.call(["curl", "-L", "--fail", "-sS", "-C", "-", "--connect-timeout", "20", "-o", gz, base + "/" + e["gz"]])
        if rc == 0: break
        print("retry", attempt, e["gz"])
    else:
        sys.exit("ERROR: download failed: " + e["gz"])
    if sha(gz) != e["gz_sha256"]:
        sys.exit("ERROR: checksum mismatch for " + e["gz"])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = dest + ".part"
    with gzip.open(gz, "rb") as src, open(part, "wb") as out:
        shutil.copyfileobj(src, out, 1 << 22)
    if sha(part) != e["sha256"]:
        os.remove(part); sys.exit("ERROR: checksum mismatch after unpacking " + e["dest"])
    os.replace(part, dest); os.remove(gz)
    print("installed:", e["dest"], "(%d bytes)" % e["bytes"])
print("DATA_OK")
PY
echo "Optional next step for verse attribution (who wrote this verse?): bash scripts/ensure_poetry_db.sh"
