#!/bin/bash
# Explicit opt-in terminal observer for local SIMORGH development.
# Disabled by default. It only talks to the local SIMORGH API.

if [[ "${SIMORGH_TERMINAL_OBSERVER_ENABLE:-0}" != "1" ]]; then
    return 0 2>/dev/null || exit 0
fi

export SIMORGH_LOG="${SIMORGH_LOG:-$HOME/simorgh/data/terminal.log}"
export SIMORGH_API="${SIMORGH_API:-http://127.0.0.1:8000/terminal/learn}"

# Authentication is never hard-coded here.
# Configure explicitly before sourcing this file when the API requires it:
#   export SIMORGH_TERMINAL_TOKEN='...'

function log_command() {
    if [[ -n "$LASTCMD" ]]; then
        mkdir -p "$(dirname "$SIMORGH_LOG")"
        printf '%s CMD: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$LASTCMD" >> "$SIMORGH_LOG"

        if [[ -n "${SIMORGH_TERMINAL_TOKEN:-}" ]]; then
            curl -sS --fail-with-body \
                --connect-timeout 1 \
                --max-time 3 \
                -X POST "$SIMORGH_API" \
                -H "Content-Type: application/json" \
                -H "x-token: $SIMORGH_TERMINAL_TOKEN" \
                -d "{\"command\":\"${LASTCMD//\"/\\\"}\",\"timestamp\":\"$(date -Iseconds)\"}" \
                >/dev/null 2>&1 || true
        fi
    fi
}

PROMPT_COMMAND="log_command; ${PROMPT_COMMAND:-}"
trap 'LASTCMD=$(history 1 | sed "s/^[ ]*[0-9]*[ ]*//")' DEBUG
