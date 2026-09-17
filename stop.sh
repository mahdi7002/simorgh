#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/simorgh"
ENV_FILE="$CONFIG_DIR/runtime.env"

if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    source "$ENV_FILE"
fi

RUNTIME_DIR="${SIMORGH_RUNTIME_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/simorgh}"
PID_FILE="$RUNTIME_DIR/simorgh.pid"

if command -v systemctl >/dev/null 2>&1 && systemctl --user list-unit-files simorgh.service >/dev/null 2>&1; then
    systemctl --user stop simorgh.service 2>/dev/null || true
fi
BACKEND_PID_FILE="$RUNTIME_DIR/llama-server.pid"

stopped=0
if command -v systemctl >/dev/null 2>&1 && systemctl --user is-active --quiet simorgh.service 2>/dev/null; then
    stopped=1
    systemctl --user stop simorgh.service 2>/dev/null || true
fi

for pid_file in "$PID_FILE" "$BACKEND_PID_FILE"; do
    if [ -f "$pid_file" ]; then
        pid="$(cat "$pid_file" 2>/dev/null || true)"
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null || true
            stopped=1
        fi
        rm -f "$pid_file"
    fi
done

if [ "$stopped" -eq 1 ]; then
    printf 'سیمرغ متوقف شد.\n'
else
    printf 'سیمرغ در حال اجرا نبود.\n'
fi
