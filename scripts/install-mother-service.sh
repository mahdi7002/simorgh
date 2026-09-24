#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
SIMORGH_REPO="${SIMORGH_MOTHER_ROOT:-$ROOT}"
UNIT_SRC="$ROOT/systemd/simorgh-mother.service.in"
UNIT_TMP="$(mktemp)"
trap 'rm -f "$UNIT_TMP"' EXIT

if [ ! -d "$SIMORGH_REPO" ]; then
    printf 'خطا: SIMORGH repo پیدا نشد: %s\n' "$SIMORGH_REPO" >&2
    exit 1
fi

if [ ! -x "$SIMORGH_REPO/.venv/bin/python" ]; then
    printf 'خطا: Python runtime سیمرغ پیدا نشد: %s\n' "$SIMORGH_REPO/.venv/bin/python" >&2
    printf 'برای بررسی worktree می‌توانید SIMORGH_MOTHER_ROOT را به repo آزمایشی تنظیم کنید.\n' >&2
    exit 1
fi

journal_groups=""
for group in adm systemd-journal; do
    if getent group "$group" >/dev/null 2>&1; then
        if [ -n "$journal_groups" ]; then
            journal_groups="$journal_groups "
        fi
        journal_groups="$journal_groups$group"
    fi
done
if [ -z "$journal_groups" ]; then
    printf 'هشدار: گروه خواندنی journal پیدا نشد؛ Mother با دسترسی محدود ادامه می‌دهد.\n' >&2
fi

sed \
    -e "s#__SIMORGH_USER__#$USER_NAME#g" \
    -e "s#__SIMORGH_HOME__#$HOME_DIR#g" \
    -e "s#__SIMORGH_REPO__#$SIMORGH_REPO#g" \
    -e "s#__JOURNAL_GROUPS__#$journal_groups#g" \
    "$UNIT_SRC" > "$UNIT_TMP"


sudo install -m 0644 "$UNIT_TMP" /etc/systemd/system/simorgh-mother.service
sudo install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$HOME_DIR/.local/share/simorgh/mother"
sudo install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$HOME_DIR/.local/share/simorgh/memory"
sudo systemctl daemon-reload
sudo systemctl enable --now simorgh-mother.service

printf 'SIMORGH Mother فعال شد.\n'
printf 'repo: %s\n' "$SIMORGH_REPO"
sudo systemctl status simorgh-mother.service --no-pager -l
