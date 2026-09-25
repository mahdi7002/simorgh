from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "SIMORGH_MOTHER_BILINGUAL_ACTIVITY_V1"

DEFAULT_POLICY = {
    "system_language": "fa",
    "interaction_language": "fa",
    "always_store": ["fa", "en"],
    "audience": "child",
    "simple_language": True,
}


def _mother_dir() -> Path:
    configured = os.environ.get("SIMORGH_MOTHER_DB", "").strip()

    if configured:
        return Path(configured).expanduser().resolve().parent

    return (
        Path.home()
        / ".local"
        / "share"
        / "simorgh"
        / "mother"
    )


def activity_path() -> Path:
    return _mother_dir() / "bilingual_activity.jsonl"


def latest_path() -> Path:
    return _mother_dir() / "bilingual_activity_latest.json"


def policy_path() -> Path:
    return _mother_dir() / "language_policy.json"


def ensure_storage() -> None:
    directory = _mother_dir()
    directory.mkdir(parents=True, exist_ok=True)

    path = activity_path()

    if not path.exists():
        path.touch(mode=0o600)

    policy = policy_path()

    if not policy.exists():
        policy.write_text(
            json.dumps(
                DEFAULT_POLICY,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            policy.chmod(0o600)
        except OSError:
            pass


def load_policy() -> dict[str, Any]:
    ensure_storage()

    try:
        data = json.loads(
            policy_path().read_text(encoding="utf-8")
        )
    except Exception:
        data = {}

    policy = dict(DEFAULT_POLICY)
    policy.update(
        {
            key: value
            for key, value in data.items()
            if value is not None
        }
    )

    if policy["system_language"] not in {"fa", "en"}:
        policy["system_language"] = "fa"

    if policy["interaction_language"] not in {
        "fa",
        "en",
        "auto",
    }:
        policy["interaction_language"] = "fa"

    if policy["audience"] not in {
        "child",
        "simple",
        "normal",
        "technical",
    }:
        policy["audience"] = "child"

    policy["always_store"] = ["fa", "en"]
    policy["simple_language"] = True

    return policy


def save_policy(
    *,
    system_language: str | None = None,
    interaction_language: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:

    policy = load_policy()

    if system_language is not None:
        if system_language not in {"fa", "en"}:
            raise ValueError("system_language must be fa or en")
        policy["system_language"] = system_language

    if interaction_language is not None:
        if interaction_language not in {"fa", "en", "auto"}:
            raise ValueError(
                "interaction_language must be fa, en, or auto"
            )
        policy["interaction_language"] = interaction_language

    if audience is not None:
        if audience not in {
            "child",
            "simple",
            "normal",
            "technical",
        }:
            raise ValueError("invalid audience")

        policy["audience"] = audience

    policy["always_store"] = ["fa", "en"]
    policy["simple_language"] = True

    ensure_storage()

    policy_path().write_text(
        json.dumps(
            policy,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return policy


_SECRET_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|cookie)",
    re.I,
)


def _sanitize(
    value: Any,
    depth: int = 0,
) -> Any:

    if depth >= 4:
        return "[TRUNCATED]"

    if isinstance(value, dict):
        result = {}

        for key, item in list(value.items())[:40]:
            key_text = str(key)

            if _SECRET_KEY.search(key_text):
                result[key_text] = "[REDACTED]"
                continue

            result[key_text] = _sanitize(
                item,
                depth + 1,
            )

        if len(value) > 40:
            result["__truncated_keys__"] = len(value) - 40

        return result

    if isinstance(value, list):
        return [
            _sanitize(item, depth + 1)
            for item in value[:20]
        ]

    if isinstance(value, str):
        return value[:1000]

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    return str(value)[:1000]


def _value(data: dict[str, Any], key: str) -> str:
    value = data.get(key)

    if value is None:
        return ""

    return str(value)


def narrate_event(
    *,
    event_type: str,
    actor: str,
    action: str,
    severity: str,
    verified: bool,
    provenance: str | None,
    data: dict[str, Any] | None,
) -> tuple[str, str]:

    data = data or {}

    if event_type == "observer_started":
        fa = "مادر سیمرغ شروع به دیدن وضعیت سیستم کرد."
        en = "SIMORGH Mother started watching the system."

    elif event_type == "observer_error":
        error_type = _value(data, "type") or "نامشخص"
        fa = (
            f"مادر هنگام دیدن سیستم به یک خطا رسید. "
            f"نوع خطا: {error_type}."
        )
        en = (
            "Mother found an error while watching the system. "
            f"Error type: {error_type}."
        )

    elif event_type == "journal_activity":
        fa = "مادر فعالیت‌های دفترچهٔ سیستم را دید و ثبت کرد."
        en = "Mother saw and recorded system journal activity."

    elif event_type == "journal_unavailable":
        fa = "دفترچهٔ سیستم در این لحظه در دسترس نبود."
        en = "The system journal was not available at this moment."

    elif event_type == "state_changed":
        fa = "مادر یک تغییر در وضعیت سیستم را دید."
        en = "Mother saw a change in the system state."

    elif event_type == "gemma_report_generated":
        fa = (
            "Gemma یک گزارش محلی ساخت. "
            "این گزارش به‌تنهایی حقیقت را ثابت نمی‌کند."
        )
        en = (
            "Gemma created a local report. "
            "The report alone does not prove the truth of every claim."
        )

    elif event_type == "quarantine_fetch_failed":
        fa = "گرفتن یک منبع برای بررسی بیشتر با خطا روبه‌رو شد."
        en = "Fetching a source for further review failed."

    elif event_type == "quarantine_approved":
        fa = "یک منبع پس از بررسی انسانی پذیرفته شد."
        en = "A source was accepted after human review."

    elif event_type == "quarantine_rejected":
        fa = "یک منبع پس از بررسی انسانی رد شد."
        en = "A source was rejected after human review."

    elif event_type in {
        "coding_proposed",
        "code_repair_proposed",
    }:
        fa = "یک پیشنهاد برای تغییر کد ثبت شد."
        en = "A proposal to change code was recorded."

    elif event_type in {
        "coding_verified",
        "code_repair_verified",
    }:
        fa = "یک تغییر پیشنهادی کد با آزمون بررسی شد."
        en = "A proposed code change was checked with tests."

    elif event_type in {
        "coding_applied",
        "code_repair_applied",
    }:
        fa = "یک تغییر کد پس از تأیید انسانی اعمال شد."
        en = "A code change was applied after human approval."

    elif event_type == "ai_work_logged":
        fa = "یک فعالیت کاری هوش مصنوعی در دفتر ثبت شد."
        en = "An AI work activity was recorded."

    else:
        # Safe generic narration. Never invents the cause.
        fa = (
            f"مادر یک رخداد را ثبت کرد: {event_type}. "
            f"عامل: {actor or 'نامشخص'}."
        )
        en = (
            f"Mother recorded an event: {event_type}. "
            f"Actor: {actor or 'unknown'}."
        )

    if not verified:
        fa += " این رخداد هنوز به‌طور مستقل تأیید نشده است."
        en += " This event has not been independently verified."

    return fa, en


def _event_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def record_bilingual_event(
    *,
    event_type: str,
    actor: str,
    action: str,
    severity: str,
    verified: bool,
    provenance: str | None,
    data: dict[str, Any] | None,
    timestamp: str | None = None,
) -> dict[str, Any]:

    ensure_storage()

    policy = load_policy()

    timestamp = timestamp or datetime.now(
        timezone.utc
    ).isoformat()

    clean_data = _sanitize(data or {})

    fa, en = narrate_event(
        event_type=event_type,
        actor=actor,
        action=action,
        severity=severity,
        verified=verified,
        provenance=provenance,
        data=clean_data,
    )

    payload = {
        "schema_version": SCHEMA_VERSION,
        "event_id": str(uuid4()),
        "timestamp": timestamp,
        "event_type": event_type,
        "actor": actor,
        "action": action,
        "severity": severity,
        "fact": {
            "verified": bool(verified),
            "provenance": provenance or "unknown",
        },
        "language": policy,
        "narration": {
            "fa": fa,
            "en": en,
        },
        "data": clean_data,
    }

    payload["event_sha256"] = _event_hash(payload)

    line = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        + "\n"
    )

    path = activity_path()

    with path.open(
        "a",
        encoding="utf-8",
    ) as f:
        f.write(line)
        f.flush()
        os.fsync(f.fileno())

    latest_path().write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        latest_path().chmod(0o600)
    except OSError:
        pass

    return payload


def install_ledger_bridge(ledger_class: type) -> None:
    marker = "_simorgh_bilingual_bridge_installed"

    if getattr(ledger_class, marker, False):
        return

    original = ledger_class.record_event

    def wrapped(self, *args, **kwargs):
        # Preserve MotherLedger.record_event API exactly.
        result = original(
            self,
            *args,
            **kwargs,
        )

        try:
            event_type = kwargs.get("event_type")
            actor = kwargs.get("actor", "")
            action = kwargs.get("action")
            severity = kwargs.get("severity", "info")
            verified = kwargs.get("verified", False)
            provenance = kwargs.get(
                "provenance",
                "system_observation",
            )
            data = kwargs.get("data")

            # All current calls use keyword-only arguments.
            # Defaults above mirror MotherLedger.record_event.
            if provenance is None:
                provenance = "system_observation"

            record_bilingual_event(
                event_type=str(event_type or "unknown"),
                actor=str(actor or ""),
                action=str(action or ""),
                severity=str(severity or "info"),
                verified=bool(verified),
                provenance=str(provenance),
                data=data,
            )

        except Exception as exc:
            # Narration is a sidecar and must never break Mother.
            logger.error(
                "bilingual activity write failed: %s",
                exc,
            )

        return result

    wrapped.__name__ = getattr(
        original,
        "__name__",
        "record_event",
    )

    setattr(
        ledger_class,
        "record_event",
        wrapped,
    )

    setattr(
        ledger_class,
        marker,
        True,
    )


def interaction_text(
    fa: str,
    en: str,
) -> str:
    policy = load_policy()

    language = policy["interaction_language"]

    if language == "en":
        return en

    # fa and auto both default to Persian-first interaction.
    return fa


__all__ = [
    "SCHEMA_VERSION",
    "activity_path",
    "latest_path",
    "policy_path",
    "ensure_storage",
    "load_policy",
    "save_policy",
    "record_bilingual_event",
    "install_ledger_bridge",
    "narrate_event",
    "interaction_text",
]
