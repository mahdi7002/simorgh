#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
FLAG=0

echo "=== قانون ۱: کپی دوم در دیسک؟ ==="
for d in "$HOME"/simorgh-*; do
  case "$(basename "$d")" in
    simorgh-mother-review|simorgh-agent-lab|simorgh-vec|simorgh-*-backups|simorgh-*-archive|simorgh-reconciliation-*|simorgh-db-backups) continue ;;
  esac
  if [ -d "$d" ] && [ "$d" != "$HOME/simorgh" ] && [ "$d" != "$HOME/simorgh-mother-review" ] && [ "$d" != "$HOME/simorgh-agent-lab" ]; then
    echo "  هشدار: $d پیدا شد"
    FLAG=1
  fi
done

echo "=== قانون ۴: برنچ‌های ساب‌سیستم خودمختار عقب‌مانده از main ==="
for b in $(git branch -r | grep -iE "mother|agent|autonom"); do
  behind=$(git rev-list --count "$b"..origin/main 2>/dev/null || echo "?")
  if [ "$behind" != "0" ] && [ "$behind" != "?" ]; then
    echo "  هشدار: $b از main عقب‌تر است ($behind کامیت)"
    FLAG=1
  fi
done

if [ "$FLAG" = "1" ]; then
  echo ""
  echo "توقف: موارد بالا باید قبل از شروع کار جدید با مهدی مطرح شود."
  exit 1
else
  echo "همه‌چیز طبق BUILD_PRINCIPLES.md تمیز است — ادامه بده."
fi
