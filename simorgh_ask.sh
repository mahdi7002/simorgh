#!/bin/bash
# simorgh_ask.sh
# با کلیک روی آیکون اجرا می‌شه: یه سوال می‌پرسه، از سیمرغ جواب می‌گیره، نشون می‌ده.

QUESTION=$(zenity --entry \
  --title="سیمرغ" \
  --text="با سیمرغ چی کار داری؟" \
  --width=400)

# اگه کاربر Cancel زد یا چیزی ننوشت، خارج شو
if [ -z "$QUESTION" ]; then
  exit 0
fi

(
  echo "10"
  echo "# سیمرغ داره فکر می‌کنه..."
) | zenity --progress --pulsate --no-cancel --auto-close --title="سیمرغ" &
PROGRESS_PID=$!

ANSWER=$(cd /home/mahdi/simorgh && SIMORGH_Q="$QUESTION" /home/mahdi/SimorghCore/venv/bin/python3 -c "
import os
from core.chat import ask
print(ask(os.environ['SIMORGH_Q']))
" 2>/home/mahdi/SimorghCore/data/simorgh_ask_error.log)

kill "$PROGRESS_PID" 2>/dev/null

if [ -z "$ANSWER" ]; then
  ANSWER="یه مشکلی پیش اومد. لاگ خطا: /home/mahdi/SimorghCore/data/simorgh_ask_error.log"
fi

echo "$ANSWER" | zenity --text-info \
  --title="پاسخ سیمرغ" \
  --width=500 --height=350
