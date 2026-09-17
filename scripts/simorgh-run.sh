#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/simorgh"
ENV_FILE="$CONFIG_DIR/runtime.env"
VENV="$ROOT/.venv/bin/python"

if [ ! -x "$VENV" ]; then
    printf 'خطا: محیط Python سیمرغ پیدا نشد: %s\n' "$VENV" >&2
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

export SIMORGH_RUNTIME_DIR="${SIMORGH_RUNTIME_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/simorgh}"
export SIMORGH_MEMORY_DIR="${SIMORGH_MEMORY_DIR:-$SIMORGH_RUNTIME_DIR/memory}"
export SIMORGH_LOG_DIR="${SIMORGH_LOG_DIR:-$SIMORGH_RUNTIME_DIR/logs}"
export SIMORGH_APP_DB="${SIMORGH_APP_DB:-$SIMORGH_RUNTIME_DIR/data/simorgh.db}"
export SIMORGH_BOOKS_DB="${SIMORGH_BOOKS_DB:-$SIMORGH_RUNTIME_DIR/data/books.db}"
export SIMORGH_LIBRARY_DB="${SIMORGH_LIBRARY_DB:-$SIMORGH_RUNTIME_DIR/data/library_catalog.db}"
export SIMORGH_JOURNAL_DB="${SIMORGH_JOURNAL_DB:-$SIMORGH_RUNTIME_DIR/memory/journal.db}"
export SIMORGH_ACTIVITY_DB="${SIMORGH_ACTIVITY_DB:-$SIMORGH_RUNTIME_DIR/data/activity.db}"
export SIMORGH_IMPORTS_DIR="${SIMORGH_IMPORTS_DIR:-$SIMORGH_RUNTIME_DIR/imports}"
export SIMORGH_TRANSCRIPTS_DIR="${SIMORGH_TRANSCRIPTS_DIR:-$SIMORGH_RUNTIME_DIR/transcripts}"
export SIMORGH_AUDIO_OUT_DIR="${SIMORGH_AUDIO_OUT_DIR:-$SIMORGH_RUNTIME_DIR/audio_out}"
export SIMORGH_PROPOSAL_DIR="${SIMORGH_PROPOSAL_DIR:-$SIMORGH_RUNTIME_DIR/data/reflection_proposals}"
export SIMORGH_HOST="${SIMORGH_HOST:-127.0.0.1}"
export SIMORGH_PORT="${SIMORGH_PORT:-8000}"

mkdir -p "$SIMORGH_RUNTIME_DIR" "$SIMORGH_MEMORY_DIR" "$SIMORGH_LOG_DIR"
cd "$ROOT"
exec "$VENV" main.py
