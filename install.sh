#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
RUNTIME_DIR="${SIMORGH_RUNTIME_DIR:-$XDG_DATA_HOME/simorgh}"
CONFIG_DIR="$XDG_CONFIG_HOME/simorgh"
ENV_FILE="$CONFIG_DIR/runtime.env"
PID_FILE="$RUNTIME_DIR/simorgh.pid"
LOG_FILE="$RUNTIME_DIR/logs/launcher.log"
VENV="$ROOT/.venv"

mkdir -p "$CONFIG_DIR" "$RUNTIME_DIR/logs"

printf '\nSIMORGH | سیمرغ\n'
printf 'اجرای محلی، بدون حساب، بدون API key و بدون اجبار به مدل.\n\n'

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    RUNTIME_DIR="${SIMORGH_RUNTIME_DIR:-$RUNTIME_DIR}"
fi

if [ ! -f "$ENV_FILE" ] && [ -t 0 ]; then
    printf 'محل داده‌های شخصی و مدل‌ها [%s]: ' "$RUNTIME_DIR"
    read -r selected || true
    if [ -n "${selected:-}" ]; then
        RUNTIME_DIR="$(eval printf '%s' "$selected")"
    fi
fi

RUNTIME_DIR="$(mkdir -p "$RUNTIME_DIR" && cd "$RUNTIME_DIR" && pwd)"
mkdir -p "$RUNTIME_DIR"/{data,memory,models,logs,imports,transcripts,audio_out}

cat > "$ENV_FILE" <<EOF
SIMORGH_RUNTIME_DIR=$(printf '%q' "$RUNTIME_DIR")
SIMORGH_MEMORY_DIR=$(printf '%q' "$RUNTIME_DIR/memory")
SIMORGH_LOG_DIR=$(printf '%q' "$RUNTIME_DIR/logs")
SIMORGH_APP_DB=$(printf '%q' "$RUNTIME_DIR/data/simorgh.db")
SIMORGH_BOOKS_DB=$(printf '%q' "$RUNTIME_DIR/data/books.db")
SIMORGH_LIBRARY_DB=$(printf '%q' "$RUNTIME_DIR/data/library_catalog.db")
SIMORGH_JOURNAL_DB=$(printf '%q' "$RUNTIME_DIR/memory/journal.db")
SIMORGH_ACTIVITY_DB=$(printf '%q' "$RUNTIME_DIR/data/activity.db")
SIMORGH_IMPORTS_DIR=$(printf '%q' "$RUNTIME_DIR/imports")
SIMORGH_TRANSCRIPTS_DIR=$(printf '%q' "$RUNTIME_DIR/transcripts")
SIMORGH_AUDIO_OUT_DIR=$(printf '%q' "$RUNTIME_DIR/audio_out")
SIMORGH_PROPOSAL_DIR=$(printf '%q' "$RUNTIME_DIR/data/reflection_proposals")
SIMORGH_HOST=127.0.0.1
EOF
# shellcheck disable=SC1090
source "$ENV_FILE"

if [ -f "$ROOT/data/simorgh_full.db" ] && [ "$(wc -c < "$ROOT/data/simorgh_full.db")" -lt 1000 ]; then
    printf 'دیتابیس LFS هنوز materialize نشده است؛ تلاش برای دریافت آن...\n'
    if ! command -v git-lfs >/dev/null 2>&1; then
        if command -v sudo >/dev/null 2>&1 && command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update -qq
            sudo apt-get install -y git-lfs >/dev/null
        fi
    fi
    if command -v git-lfs >/dev/null 2>&1; then
        git -C "$ROOT" lfs install --local >/dev/null 2>&1 || true
        git -C "$ROOT" lfs pull --include="data/simorgh_full.db"
    fi
fi

if [ -f "$ROOT/data/simorgh_full.db" ] && [ "$(wc -c < "$ROOT/data/simorgh_full.db")" -lt 1000 ]; then
    printf 'هشدار: بستهٔ دانش شعری LFS در دسترس نیست؛ هستهٔ قرآن و بقیهٔ runtime همچنان قابل اجرا هستند.\n'
fi

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
            then
                command -v "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
    printf 'خطا: Python 3.10 یا جدیدتر پیدا نشد.\n' >&2
    exit 1
fi

if [ ! -x "$VENV/bin/python" ]; then
    "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --disable-pip-version-check -q -r "$ROOT/requirements.txt"

PORT="${SIMORGH_PORT:-}"
if [ -z "$PORT" ]; then
    PORT="$($VENV/bin/python - <<'PY'
import socket
for port in range(8000, 8011):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("No free local port in 8000-8010")
PY
)"
fi
export SIMORGH_PORT="$PORT"

if [ -f "$PID_FILE" ]; then
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        printf 'سیمرغ از قبل در حال اجراست: http://127.0.0.1:%s/\n' "$PORT"
        if command -v xdg-open >/dev/null 2>&1; then xdg-open "http://127.0.0.1:$PORT/" >/dev/null 2>&1 & fi
        exit 0
    fi
    rm -f "$PID_FILE"
fi

printf 'در حال آماده‌سازی سیمرغ...\n'
(
    cd "$ROOT"
    nohup env \
        SIMORGH_RUNTIME_DIR="$SIMORGH_RUNTIME_DIR" \
        SIMORGH_MEMORY_DIR="$SIMORGH_MEMORY_DIR" \
        SIMORGH_LOG_DIR="$SIMORGH_LOG_DIR" \
        SIMORGH_APP_DB="$SIMORGH_APP_DB" \
        SIMORGH_BOOKS_DB="$SIMORGH_BOOKS_DB" \
        SIMORGH_LIBRARY_DB="$SIMORGH_LIBRARY_DB" \
        SIMORGH_JOURNAL_DB="$SIMORGH_JOURNAL_DB" \
        SIMORGH_ACTIVITY_DB="$SIMORGH_ACTIVITY_DB" \
        SIMORGH_IMPORTS_DIR="$SIMORGH_IMPORTS_DIR" \
        SIMORGH_TRANSCRIPTS_DIR="$SIMORGH_TRANSCRIPTS_DIR" \
        SIMORGH_AUDIO_OUT_DIR="$SIMORGH_AUDIO_OUT_DIR" \
        SIMORGH_PROPOSAL_DIR="$SIMORGH_PROPOSAL_DIR" \
        SIMORGH_HOST=127.0.0.1 \
        SIMORGH_PORT="$PORT" \
        "$VENV/bin/python" main.py >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
)

for _ in $(seq 1 40); do
    if "$VENV/bin/python" - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:${PORT}/health", timeout=1).read()
PY
    then
        break
    fi
    sleep 0.25
done

if ! "$VENV/bin/python" - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://127.0.0.1:${PORT}/health", timeout=2).read()
PY
then
    printf 'سیمرغ بالا نیامد. لاگ: %s\n' "$LOG_FILE" >&2
    tail -n 40 "$LOG_FILE" >&2 || true
    exit 1
fi

printf '\n✅ سیمرغ آماده است\n'
printf '🌐 http://127.0.0.1:%s/\n' "$PORT"
printf '📁 داده و مدل‌ها: %s\n' "$RUNTIME_DIR"
printf '🧠 بدون مدل: پایگاه دانش محلی فعال است.\n'
printf '🔐 حساب/API key/Telemetry اجباری نیست.\n'

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "http://127.0.0.1:$PORT/" >/dev/null 2>&1 &
fi
