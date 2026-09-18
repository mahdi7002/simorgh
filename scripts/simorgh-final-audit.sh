#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAIL=0
ok() { printf 'PASS  %s\n' "$*"; }
warn() { printf 'WARN  %s\n' "$*"; }
fail() { printf 'FAIL  %s\n' "$*" >&2; FAIL=1; }

printf '%s\n' '=== SIMORGH FINAL OPERATIONAL AUDIT ==='
printf 'ROOT=%s\n' "$ROOT"
printf 'DATE=%s\n' "$(date -Is)"

printf '%s\n' '--- Git ---'
HEAD="$(git rev-parse HEAD 2>/dev/null || true)"
REMOTE="$(git rev-parse origin/main 2>/dev/null || true)"
if [ -n "$HEAD" ]; then ok "HEAD=$HEAD"; else fail "not a git repository"; fi
if [ -n "$REMOTE" ]; then printf 'INFO  origin/main=%s\n' "$REMOTE"; else warn "origin/main unavailable"; fi
if [ -n "$(git status --porcelain)" ]; then
    warn "working tree is not clean:"
    git status --short
else
    ok "working tree clean"
fi

printf '%s\n' '--- Python/runtime ---'
if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
else
    PY="$(command -v python3 || true)"
fi
if [ -z "$PY" ]; then
    fail "Python 3.10+ not found"
else
    VERSION="$("$PY" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
    printf 'INFO  python=%s version=%s\n' "$PY" "$VERSION"
    "$PY" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
    ok "Python >= 3.10"
fi

printf '%s\n' '--- Tests & syntax ---'
PYTHONPATH=. "$PY" -m pytest -q || fail "pytest suite failed"
bash -n install.sh || fail "install.sh syntax"
bash -n stop.sh || fail "stop.sh syntax"
bash -n scripts/simorgh-run.sh || fail "simorgh-run.sh syntax"
ok "shell syntax checks completed"

printf '%s\n' '--- Canonical LFS database ---'
if [ -f data/simorgh_full.db ]; then
    SIZE="$(stat -c '%s' data/simorgh_full.db)"
    printf 'INFO  data/simorgh_full.db=%s bytes\n' "$SIZE"
    if [ "$SIZE" -lt 1000000 ]; then
        fail "canonical database is unexpectedly small; LFS may not be materialized"
    else
        POINTER="$(git show HEAD:data/simorgh_full.db 2>/dev/null || true)"
        EXPECTED_SHA="$(printf '%s\n' "$POINTER" | sed -n 's/^oid sha256://p' | head -n1)"
        if printf '%s' "$EXPECTED_SHA" | grep -Eq '^[0-9a-f]{64}$'; then
            ACTUAL_SHA="$(sha256sum data/simorgh_full.db | awk '{print $1}')"
            if [ "$ACTUAL_SHA" = "$EXPECTED_SHA" ]; then
                ok "canonical DB SHA-256 matches Git LFS pointer: $ACTUAL_SHA"
            else
                fail "canonical DB SHA mismatch: expected $EXPECTED_SHA actual $ACTUAL_SHA"
            fi
        else
            warn "could not read an LFS pointer from HEAD; verifying file directly only"
        fi
        if command -v sqlite3 >/dev/null 2>&1; then
            [ "$(sqlite3 -readonly data/simorgh_full.db 'PRAGMA integrity_check;')" = "ok" ]                 && ok "SQLite integrity_check=ok"                 || fail "SQLite integrity_check failed"
        else
            "$PY" - <<'PY'
import sqlite3
conn = sqlite3.connect("data/simorgh_full.db")
try:
    result = conn.execute("PRAGMA integrity_check;").fetchone()[0]
finally:
    conn.close()
raise SystemExit(0 if result == "ok" else 1)
PY
            ok "SQLite integrity_check=ok (Python sqlite3)"
        fi
    fi
else
    fail "data/simorgh_full.db is missing"
fi

printf '%s\n' '--- Runtime configuration ---'
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/simorgh/runtime.json"
ENV_FILE="${XDG_CONFIG_HOME:-$HOME/.config}/simorgh/runtime.env"
if [ -f "$CONFIG" ]; then
    ok "runtime config exists: $CONFIG"
else
    fail "runtime config missing: $CONFIG"
fi
if [ -f "$ENV_FILE" ]; then
    ok "runtime env exists: $ENV_FILE"
else
    fail "runtime env missing: $ENV_FILE"
fi

PORT="$("$PY" - "$CONFIG" <<'PY' 2>/dev/null || true
import json, sys
try:
    print(int(json.load(open(sys.argv[1], encoding="utf-8"))["port"]))
except Exception:
    pass
PY
)"
if [ -n "$PORT" ]; then
    printf 'INFO  port=%s\n' "$PORT"
else
    fail "runtime port could not be read"
fi

printf '%s\n' '--- systemd user service ---'
if command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user is-enabled simorgh.service >/dev/null 2>&1 && ok "simorgh.service enabled" || fail "simorgh.service not enabled"
    systemctl --user is-active simorgh.service >/dev/null 2>&1 && ok "simorgh.service active" || fail "simorgh.service not active"

    UNIT="$(systemctl --user cat simorgh.service 2>/dev/null || true)"
    printf '%s\n' "$UNIT" | grep -q 'Restart=always' && ok "Restart=always" || fail "Restart=always missing"
    printf '%s\n' "$UNIT" | grep -q 'UMask=0077' && ok "UMask=0077" || fail "UMask=0077 missing"
    printf '%s\n' "$UNIT" | grep -q 'NoNewPrivileges=true' && ok "NoNewPrivileges=true" || fail "NoNewPrivileges missing"

    PID="$(systemctl --user show -p MainPID --value simorgh.service)"
    if [ -n "$PID" ] && [ "$PID" != "0" ]; then
        CMD="$(ps -p "$PID" -o args= 2>/dev/null || true)"
        printf 'INFO  MainPID=%s\n' "$PID"
        printf 'INFO  cmd=%s\n' "$CMD"
        printf '%s\n' "$CMD" | grep -Fq "$ROOT/.venv/bin/python"             && ok "service uses repo-local Python"             || fail "service is not using repo-local Python"
        printf '%s\n' "$CMD" | grep -Fq 'main.py'             && ok "service command is main.py"             || fail "service command does not contain main.py"
    else
        fail "MainPID unavailable"
    fi
else
    warn "systemd user manager unavailable; persistent service checks skipped"
fi

printf '%s\n' '--- Legacy system service ---'
OLD_STATE="$(systemctl is-active simorgh-core.service 2>/dev/null || true)"
OLD_ENABLED="$(systemctl is-enabled simorgh-core.service 2>/dev/null || true)"
printf 'INFO  simorgh-core.service active=%s enabled=%s\n' "${OLD_STATE:-unknown}" "${OLD_ENABLED:-unknown}"
[ "$OLD_STATE" = "inactive" ] || [ "$OLD_STATE" = "failed" ] || [ -z "$OLD_STATE" ]     && ok "legacy service is not active"     || fail "legacy simorgh-core.service is still active"

printf '%s\n' '--- HTTP runtime ---'
if [ -n "$PORT" ]; then
    HEALTH="$(curl -fsS "http://127.0.0.1:$PORT/health" 2>/dev/null || true)"
    if [ -n "$HEALTH" ]; then
        printf 'INFO  health=%s\n' "$HEALTH"
        printf '%s\n' "$HEALTH" | grep -q '"status":"healthy"'             && ok "health status=healthy"             || fail "health status is not healthy"
        "$PY" - "$HEALTH" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
raise SystemExit(0 if data.get("python_version") else 1)
PY
        ok "health exposes Python version"
    else
        fail "health endpoint unavailable on 127.0.0.1:$PORT"
    fi

    ROOT_HTML="$(curl -fsS "http://127.0.0.1:$PORT/" 2>/dev/null || true)"
    printf '%s' "$ROOT_HTML" | grep -q 'SIMORGH'         && ok "root UI responds"         || fail "root UI missing/unavailable"

    BOOTSTRAP="$(curl -fsS "http://127.0.0.1:$PORT/api/bootstrap" 2>/dev/null || true)"
    "$PY" - "$BOOTSTRAP" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
knowledge = data.get("knowledge", {})
raise SystemExit(0 if knowledge.get("database_first") and knowledge.get("requires_model") is False else 1)
PY
    ok "bootstrap reports Database-First without model requirement"
else
    warn "HTTP checks skipped because port is unknown"
fi

printf '%s\n' '--- Optional crash-recovery test ---'
if [ "${1:-}" = "--crash-test" ]; then
    if ! command -v systemctl >/dev/null 2>&1 || ! systemctl --user is-active --quiet simorgh.service 2>/dev/null; then
        fail "cannot run crash test: simorgh.service is not active"
    else
        OLD_PID="$(systemctl --user show -p MainPID --value simorgh.service)"
        printf 'INFO  killing MainPID=%s\n' "$OLD_PID"
        kill -9 "$OLD_PID"
        NEW_PID=""
        for _ in $(seq 1 40); do
            sleep 0.25
            NEW_PID="$(systemctl --user show -p MainPID --value simorgh.service 2>/dev/null || true)"
            [ -n "$NEW_PID" ] && [ "$NEW_PID" != "0" ] && [ "$NEW_PID" != "$OLD_PID" ] && break
        done
        if [ "$NEW_PID" != "" ] && [ "$NEW_PID" != "0" ] && [ "$NEW_PID" != "$OLD_PID" ]; then
            ok "service auto-restarted: $OLD_PID -> $NEW_PID"
            curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null                 && ok "health recovered after crash"                 || fail "health did not recover after crash"
        else
            fail "service did not obtain a new MainPID after crash"
        fi
    fi
else
    printf 'INFO  pass --crash-test to exercise Restart=always destructively\n'
fi

printf '%s\n' '=== RESULT ==='
if [ "$FAIL" -eq 0 ]; then
    printf '%s\n' 'PASS  SIMORGH FINAL OPERATIONAL AUDIT'
else
    printf '%s\n' 'FAIL  SIMORGH FINAL OPERATIONAL AUDIT'
fi
exit "$FAIL"
