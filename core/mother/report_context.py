from __future__ import annotations

import hashlib
import json
from typing import Any


def _shrink(
    value: Any,
    *,
    max_depth: int = 3,
    max_string: int = 450,
    max_list: int = 6,
    max_dict: int = 20,
    depth: int = 0,
) -> Any:
    if depth >= max_depth:
        return "[COMPACTED_DEPTH]"

    if isinstance(value, str):
        if len(value) <= max_string:
            return value
        return value[:max_string] + "…"

    if isinstance(value, (int, float, bool)) or value is None:
        return value

    if isinstance(value, list):
        return [
            _shrink(
                item,
                max_depth=max_depth,
                max_string=max_string,
                max_list=max_list,
                max_dict=max_dict,
                depth=depth + 1,
            )
            for item in value[:max_list]
        ]

    if isinstance(value, dict):
        result = {}

        for key, item in list(value.items())[:max_dict]:
            result[str(key)] = _shrink(
                item,
                max_depth=max_depth,
                max_string=max_string,
                max_list=max_list,
                max_dict=max_dict,
                depth=depth + 1,
            )

        if len(value) > max_dict:
            result["__truncated_keys__"] = len(value) - max_dict

        return result

    return str(value)[:max_string]


def _compact_systemd(snapshot: dict[str, Any]) -> dict[str, Any]:
    units = ((snapshot.get("systemd") or {}).get("units") or {})

    names = (
        "llama-server.service",
        "simorgh-mother.service",
        "simorgh.service",
        "simorgh-core.service",
        "simorgh-persona.service",
    )

    result = {}

    for name in names:
        unit = units.get(name)

        if not isinstance(unit, dict):
            continue

        result[name] = {
            "active": unit.get("active"),
            "load": unit.get("load"),
            "sub": unit.get("sub"),
        }

    return result


def _compact_ports(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    result = []

    for item in snapshot.get("ports") or []:
        if not isinstance(item, dict):
            continue

        local = str(item.get("local", ""))

        if not any(
            marker in local
            for marker in (
                "127.0.0.1:8000",
                "127.0.0.1:8010",
                "127.0.0.1:8080",
                "127.0.0.1:8081",
            )
        ):
            continue

        result.append({
            "local": local,
        })

    return result[:6]


def compact_snapshot(
    snapshot: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(snapshot, dict):
        return None

    cpu = snapshot.get("cpu") or {}
    memory = snapshot.get("memory") or {}
    swap = snapshot.get("swap") or {}
    disk = snapshot.get("disk") or {}
    os_info = snapshot.get("os") or {}
    access = snapshot.get("access") or {}
    processes = snapshot.get("processes") or {}

    return {
        "timestamp": snapshot.get("timestamp"),
        "host": snapshot.get("host"),

        "os": {
            "system": os_info.get("system"),
            "release": os_info.get("release"),
            "machine": os_info.get("machine"),
            "python": os_info.get("python"),
        },

        "cpu": {
            "logical": cpu.get("logical"),
            "physical": cpu.get("physical"),
            "percent": cpu.get("percent"),
        },

        "memory": {
            "total_mb": memory.get("total_mb"),
            "available_mb": memory.get("available_mb"),
            "percent": memory.get("percent"),
        },

        "swap": {
            "total_mb": swap.get("total_mb"),
            "used_mb": swap.get("used_mb"),
            "percent": swap.get("percent"),
        },

        "disk": {
            "free_gb": disk.get("free_gb"),
            "percent": disk.get("percent"),
        },

        "access": {
            "journal_readable": access.get("journal_readable"),
        },

        "systemd": _compact_systemd(snapshot),
        "ports": _compact_ports(snapshot),

        "processes": {
            "total_count": processes.get("total_count"),
        },
    }


def _compact_events(value: Any, limit: int = 8) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None

    items = sorted(
        (
            (str(key), val)
            for key, val in value.items()
            if isinstance(val, (int, float))
        ),
        key=lambda item: (-float(item[1]), item[0]),
    )

    return dict(items[:limit])


def compact_report(
    report: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(report, dict):
        return None

    return {
        "report_type": report.get("report_type"),
        "period": report.get("period"),
        "generated_at": report.get("generated_at"),

        "events_total": report.get("events_total"),
        "events_by_component": _compact_events(
            report.get("events_by_component"),
            6,
        ),
        "events_by_type": _compact_events(
            report.get("events_by_type"),
            8,
        ),

        "snapshots_count": report.get("snapshots_count"),

        "changes": [
            str(item)[:220]
            for item in (report.get("changes") or [])[:8]
        ],

        "vs_previous_day": _shrink(
            report.get("vs_previous_day"),
            max_depth=2,
            max_string=220,
            max_list=3,
            max_dict=8,
        ),

        "known_unknowns": [
            str(item)[:220]
            for item in (report.get("known_unknowns") or [])[:6]
        ],

        "service_needs": [
            str(item)[:220]
            for item in (report.get("service_needs") or [])[:6]
        ],
    }


def build_report_evidence(
    *,
    latest_snapshot: dict[str, Any] | None,
    daily: dict[str, Any] | None,
    weekly: dict[str, Any] | None,
    post_boot: dict[str, Any] | None,
    goals: list[dict[str, Any]],
    self_model: list[dict[str, Any]],
) -> dict[str, Any]:

    evidence = {
        "latest_snapshot": compact_snapshot(latest_snapshot),
        "daily": compact_report(daily),
        "weekly": compact_report(weekly),
        "post_boot": compact_report(post_boot),

        "goals": [
            {
                "id": item.get("id"),
                "title": str(item.get("title", ""))[:180],
                "status": item.get("status"),
                "source": item.get("source"),
                "target_date": item.get("target_date"),
            }
            for item in (goals or [])[:8]
            if isinstance(item, dict)
        ],

        "self_model": [
            {
                "key": item.get("key"),
                "value": str(item.get("value", ""))[:180],
                "source": item.get("source"),
                "status": item.get("status"),
                "observed_at": item.get("observed_at"),
            }
            for item in (self_model or [])[:8]
            if isinstance(item, dict)
        ],
    }

    # First strict compaction.
    bounded = _shrink(
        evidence,
        max_depth=3,
        max_string=260,
        max_list=5,
        max_dict=16,
    )

    # Second fallback if serialized evidence is still large.
    raw = json.dumps(
        bounded,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )

    if len(raw) > 5000:
        bounded = _shrink(
            evidence,
            max_depth=2,
            max_string=160,
            max_list=3,
            max_dict=10,
        )

    return bounded


def evidence_sha256(
    evidence: dict[str, Any],
) -> str:
    raw = json.dumps(
        evidence,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(raw).hexdigest()


def response_sha256(response: str) -> str:
    return hashlib.sha256(
        (response or "").encode("utf-8")
    ).hexdigest()


def build_verification(
    response: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "TRACEABLE",
        "evidence_sha256": evidence_sha256(evidence),
        "response_sha256": response_sha256(response),
        "claim_truth": "NOT_ESTABLISHED",
        "note": (
            "گزارش به evidence فشرده و هش‌شدهٔ Mother قابل ردیابی است؛ "
            "این وضعیت به‌تنهایی صحت هر ادعای زبانی را اثبات نمی‌کند."
        ),
    }


def _review_evidence(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """Build a smaller reviewer payload without changing report evidence."""
    allowed = (
        "latest_snapshot",
        "daily",
        "weekly",
        "post_boot",
        "observation",
    )

    def clean(value: Any) -> tuple[Any, int]:
        if isinstance(value, str):
            if value == "[COMPACTED_DEPTH]":
                return None, 1
            return value, 0

        if isinstance(value, list):
            result = []
            removed = 0
            for item in value:
                cleaned, count = clean(item)
                removed += count
                if cleaned is not None:
                    result.append(cleaned)
            return result, removed

        if isinstance(value, dict):
            result = {}
            removed = 0
            for key, item in value.items():
                cleaned, count = clean(item)
                removed += count
                if cleaned is not None:
                    result[key] = cleaned
            return result, removed

        return value, 0

    result = {}
    removed_total = 0

    for key in allowed:
        if key in evidence:
            result[key], removed = clean(evidence[key])
            removed_total += removed

    result["review_meta"] = {
        "compacted_depth_markers_removed": removed_total,
        "note": (
            "[COMPACTED_DEPTH] در evidence اصلی فقط نشان‌دهندهٔ "
            "فشرده‌سازی داخلی است و نبودن شاهد محسوب نمی‌شود."
        ),
    }

    return result


def review_report_with_gemma(
    response: str,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    from core.llm_local import generate

    review_evidence = _review_evidence(evidence)

    prompt = (
        "این گزارش توسط Gemma تولید شده است. "
        "فقط بر اساس evidence زیر آن را بازبینی کن. "
        "JSON کوتاه بده با کلیدهای status, unsupported_claims, "
        "missing_evidence, note. "
        "[COMPACTED_DEPTH] فقط نشان‌دهندهٔ فشرده‌سازی evidence در عمق ساختار است و به معنی نبودن شاهد نیست. "
        "status فقط MODEL_PASS یا MODEL_WARN یا MODEL_FAIL باشد. "
        "اگر داده کافی نیست MODEL_WARN بده. "
        "هیچ واقعیت تازه‌ای نساز.\n\n"
        "REPORT:\n"
        + (response or "")[:3000]
        + "\n\nEVIDENCE:\n"
        + json.dumps(
            review_evidence,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
    )

    raw = generate(
        (
            "تو بازبین محلی SIMORGH MOTHER هستی. "
            "فقط گزارش را بر اساس evidence بررسی کن. "
            "هیچ واقعیت تازه‌ای نساز."
        ),
        prompt,
        max_tokens=96,
        needs_quality=True,
        task_class="review",
    )

    return {
        "status": "MODEL_REVIEW" if raw else "MODEL_REVIEW_UNAVAILABLE",
        "raw": raw or "",
        "evidence_sha256": evidence_sha256(evidence),
        "review_evidence_sha256": evidence_sha256(review_evidence),
        "review_evidence_scope": [
            "latest_snapshot",
            "daily",
            "weekly",
            "post_boot",
            "observation",
        ],
        "note": (
            "بازبینی دوم توسط همان مدل است و داوری مستقل حقیقت محسوب نمی‌شود."
        ),
    }
