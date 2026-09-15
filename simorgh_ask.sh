#!/bin/bash
set -euo pipefail
# simorgh_ask.sh
# اجرای ساده پرسش از رابط گرافیکی سیمرغ

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERROR_LOG="$SCRIPT_DIR/logs/simorgh_ask_error.log"
PYTHON_BIN="${SIMORGH_PYTHON:-python3}"
mkdir -p "$SCRIPT_DIR/logs"

QUESTION=$(zenity --entry \
  --title="سیمرغ" \
  --text="با سیمرغ چی کار داری؟" \
  --width=400)

if [ -z "$QUESTION" ]; then
  exit 0
fi

(
  echo "10"
  echo "# سیمرغ داره فکر می‌کنه..."
) | zenity --progress --pulsate --no-cancel --auto-close --title="سیمرغ" &
PROGRESS_PID=$!

set +e
ANSWER=$(cd "$SCRIPT_DIR" && SIMORGH_Q="$QUESTION" "$PYTHON_BIN" -c '
import os
from core.chat import ask
print(ask(os.environ["SIMORGH_Q"]))
' 2>"$ERROR_LOG")
RC=$?
set -e

kill "$PROGRESS_PID" 2>/dev/null || true
wait "$PROGRESS_PID" 2>/dev/null || true

if [ "$RC" -ne 0 ] || [ -z "$ANSWER" ]; then
  ANSWER="یه مشکلی پیش اومد. لطفاً گزارش خطا را در $ERROR_LOG بررسی کنید."
fi

echo "$ANSWER" | zenity --text-info \
  --title="پاسخ سیمرغ" \
  --width=500 --height=350
