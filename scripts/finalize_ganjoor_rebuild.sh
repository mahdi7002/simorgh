#!/usr/bin/env bash
set -euo pipefail

DB="data/simorgh_full.db"
STAGING="rebuild_staging/ganjoor_simorgh_full.db"
SOURCE="rebuild_staging/ganjoor-data"

case "${1:-verify}" in
  verify)
    python3 scripts/rebuild_poems_from_ganjoor.py \
      --db "$DB" \
      --output "$STAGING" \
      --source-dir "$SOURCE" \
      --max-chars 0
    python3 scripts/verify_ganjoor_rebuild.py \
      --db "$STAGING" \
      --source-dir "$SOURCE"
    ;;
  apply)
    python3 scripts/verify_ganjoor_rebuild.py \
      --db "$STAGING" \
      --source-dir "$SOURCE"
    python3 scripts/rebuild_poems_from_ganjoor.py \
      --db "$DB" \
      --output "$STAGING" \
      --source-dir "$SOURCE" \
      --max-chars 0 \
      --apply
    python3 scripts/verify_ganjoor_rebuild.py \
      --db "$DB" \
      --source-dir "$SOURCE"
    ;;
  *)
    echo "usage: $0 {verify|apply}" >&2
    exit 2
    ;;
esac
