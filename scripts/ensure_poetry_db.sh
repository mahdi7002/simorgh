#!/usr/bin/env bash
# Makes sure the verse database exists (it is used for "who wrote this verse?").
# If a healthy database is already there, nothing is downloaded. Otherwise it is built on this computer from the
# public Ganjoor data export (https://ganjoor.net, data: https://github.com/ganjoor/ganjoor-data). SIMORGH ships no copy of the poems.
# Options: --yes (do not ask), --keep-source (keep the downloaded copy), --poets slug1,slug2 (a subset; default: all)
# Environment: SIMORGH_VERSE_DB, GANJOOR_SOURCE_DIR, GANJOOR_REMOTE, GANJOOR_REF, SIMORGH_VERSE_POETS, PYTHON
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${SIMORGH_VERSE_DB:-$ROOT/data/poetry/persian_poetry.db}"
PY="${PYTHON:-$ROOT/.venv/bin/python}"; [ -x "$PY" ] || PY="$(command -v python3)"
SRC="${GANJOOR_SOURCE_DIR:-$ROOT/rebuild_staging/ganjoor-data}"
REMOTE="${GANJOOR_REMOTE:-https://github.com/ganjoor/ganjoor-data.git}"
REF="${GANJOOR_REF:-$(sed -n 's/^DEFAULT_REF = "\([0-9a-f]*\)".*/\1/p' "$ROOT/scripts/rebuild_poems_from_ganjoor.py" | head -1)}"
POETS="${SIMORGH_VERSE_POETS:-all}"
YES=0; KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --yes) YES=1 ;;
    --keep-source) KEEP=1 ;;
    --poets) shift; POETS="${1:-all}" ;;
    *) echo "unknown option: $1" >&2; exit 64 ;;
  esac
  shift
done

healthy() {
  "$PY" - "$OUT" <<'PYH'
import sqlite3, sys
p = sys.argv[1]
try:
    with open(p, "rb") as f:
        if f.read(40).startswith(b"version https://git-lfs"):
            sys.exit(2)
    c = sqlite3.connect("file:%s?mode=ro" % p, uri=True)
    if c.execute("select count(*) from poets").fetchone()[0] < 1:
        sys.exit(3)
    if c.execute("select count(*) from verses").fetchone()[0] < 100:
        sys.exit(4)
    c.execute("select rowid from verses_fts where verses_fts match ? limit 1", ("خدا",)).fetchall()
except SystemExit:
    raise
except Exception:
    sys.exit(5)
PYH
}

if [ -f "$OUT" ] && healthy; then
  echo "OK: the verse database is already there ($OUT); nothing to download."
  echo "پایگاه بیتی از قبل هست؛ چیزی دانلود نشد."
  exit 0
fi
[ -n "$REF" ] || { echo "ERROR: cannot read the pinned Ganjoor commit" >&2; exit 4; }

cat <<MSG
The verse database is missing. It will be built on this computer from the public Ganjoor data export:
  site   : https://ganjoor.net
  data   : https://github.com/ganjoor/ganjoor-data  (pinned commit ${REF:0:9})
SIMORGH does not publish a copy of the poems. The data repository shows no licence file, so read the terms on ganjoor.net before redistributing anything built from it.
Size: about 0.6 GB to download and about 3 GB of disk while building (the downloaded copy is removed afterwards). Measured on an older desktop CPU (i5-4460): 54 poets took about 3 minutes and gave a 0.5 GB file; the full poet list takes longer. Poets selected: ${POETS}.
Prose paragraphs and editor comments in the source are not indexed as verses.
پایگاه بیتی خودتان روی همین رایانه از دادهٔ عمومی گنجور ساخته می‌شود؛ سیمرغ نسخه‌ای از شعرها منتشر نمی‌کند. شرایط استفاده را در ganjoor.net بخوانید.
MSG
if [ "$YES" != 1 ]; then
  if [ -t 0 ]; then
    read -r -p "Continue? / ادامه می‌دهید؟ [y/N] " ans
    case "$ans" in y|Y|yes|YES) ;; *) echo "Cancelled."; exit 1 ;; esac
  else
    echo "Not interactive: run again with --yes to proceed."; exit 3
  fi
fi

CREATED=0
if [ ! -d "$SRC/.git" ]; then
  ok=0
  for attempt in 1 2 3; do
    rm -rf "$SRC"; mkdir -p "$(dirname "$SRC")"
    if git clone --depth 1 "$REMOTE" "$SRC"; then ok=1; CREATED=1; break; fi
    echo "download failed (attempt $attempt of 3)"; sleep 5
  done
  [ "$ok" = 1 ] || { echo "ERROR: could not download the Ganjoor data" >&2; exit 5; }
fi
if [ "$(git -C "$SRC" rev-parse HEAD)" != "$REF" ]; then
  git -C "$SRC" fetch --depth 1 origin "$REF"
  git -C "$SRC" checkout --detach "$REF"
fi
[ "$(git -C "$SRC" rev-parse HEAD)" = "$REF" ] || { echo "ERROR: pinned commit mismatch" >&2; exit 6; }

mkdir -p "$(dirname "$OUT")"
"$PY" "$ROOT/scripts/build_verse_db.py" --source-dir "$SRC" --output "$OUT" --poets "$POETS"
if [ "$CREATED" = 1 ] && [ "$KEEP" = 0 ]; then rm -rf "$SRC"; echo "removed the downloaded copy."; fi
healthy && echo "DONE: $OUT" || { echo "ERROR: the new database failed the health check" >&2; exit 7; }
