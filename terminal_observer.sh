#!/bin/bash
# فعال‌سازی پایش ترمینال
export SIMORGH_LOG=~/simorgh/data/terminal.log
export SIMORGH_API="http://localhost:8000/terminal/learn"

function log_command() {
    # ثبت دستور قبلی و خروجی آن
    if [[ -n "$LASTCMD" ]]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') CMD: $LASTCMD" >> "$SIMORGH_LOG"
        # ارسال به سیمرغ
        curl -s -X POST "$SIMORGH_API" \
            -H "Content-Type: application/json" \
            -H "x-token: simorgh123" \
            -d "{\"command\":\"${LASTCMD//\"/\\\"}\",\"timestamp\":\"$(date -Iseconds)\"}" &>/dev/null
    fi
}

PROMPT_COMMAND="log_command; $PROMPT_COMMAND"
trap 'LASTCMD=$(history 1 | sed "s/^[ ]*[0-9]*[ ]*//")' DEBUG
