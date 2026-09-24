#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="${SUDO_USER:-$USER}"
HOME_DIR="$(getent passwd "$USER_NAME" | cut -d: -f6)"
UNIT_SRC="$ROOT/systemd/simorgh-mother.service.in"
UNIT_TMP="$(mktemp)"
trap 'rm -f "$UNIT_TMP"' EXIT

if [ ! -x "$ROOT/.venv/bin/python" ]; then
    printf 'خطا: Python runtime سیمرغ پیدا نشد: %s\n' "$ROOT/.venv/bin/python" >&2
    exit 1
fi

if ! getent group adm >/dev/null 2>&1; then
    printf 'هشدار: گروه adm موجود نیست؛ دسترسی به journal ممکن است محدود شود.\n' >&2
fi

sed \
    -e "s#__SIMORGH_USER__#$USER_NAME#g" \
    -e "s#__SIMORGH_HOME__#$HOME_DIR#g" \
    "$UNIT_SRC" > "$UNIT_TMP"

if ! getent group adm >/dev/null 2>&1; then
    sed -i '/^SupplementaryGroups=adm$/d' "$UNIT_TMP"
fi

sudo install -m 0644 "$UNIT_TMP" /etc/systemd/system/simorgh-mother.service
sudo install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$HOME_DIR/.local/share/simorgh/mother"
sudo install -d -m 0700 -o "$USER_NAME" -g "$USER_NAME" "$HOME_DIR/.local/share/simorgh/memory"
sudo systemctl daemon-reload
sudo systemctl enable --now simorgh-mother.service

printf 'SIMORGH Mother فعال شد.\n'
sudo systemctl status simorgh-mother.service --no-pager -l
