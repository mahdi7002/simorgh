from __future__ import annotations
from core.mother.brain_registry import discover_local_brain

import json
import os
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .coding import apply_verified_patch, propose_patch, verify_patch
from core.identity import SIMORGH_IDENTITY
from core.llm_local import generate
from core.user_runtime import load_config
from .ledger import MotherLedger
from .research import (
    advisory_ai_review,
    approve_to_memory,
    browser_search_urls,
    fetch_to_quarantine,
    reject,
)
from .reports import ReportEngine
from .observer import SystemObserver
from .report_context import build_report_evidence, build_verification, review_report_with_gemma

router = APIRouter(prefix="/api/mother", tags=["mother"])

ledger = MotherLedger()
reports = ReportEngine(ledger)
observer = SystemObserver()


class GoalRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    target_date: str | None = Field(default=None, max_length=40)


class ResearchURLRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class ReviewRequest(BaseModel):
    note: str = Field(default="", max_length=1000)


class CodeRepairRequest(BaseModel):
    task: str = Field(min_length=5, max_length=4000)
    paths: list[str] = Field(default_factory=list)


class ApplyRepairRequest(BaseModel):
    approve: bool = False
    note: str = Field(default="", max_length=1000)


@router.get("/state")
def state() -> dict[str, Any]:
    boot = ledger.begin_boot()
    return {
        "boot": boot,
        "snapshot": ledger.latest_snapshot() or observer.capture(),
        "daily": ledger.latest_report("DAILY"),
        "weekly": ledger.latest_report("WEEKLY"),
        "post_boot": ledger.latest_report("POST_BOOT"),
        "goals": ledger.list_goals(),
        "self_model": ledger.list_self_model(),
        "quarantine": ledger.list_quarantine(limit=20),
        "code_repairs": ledger.list_code_repairs(limit=20),
    }


@router.get("/changes")
def changes(since: str | None = None, limit: int = 500):
    if since:
        start = since[:64]
    else:
        from datetime import datetime, timedelta, timezone
        start = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    return {"since": start, "events": ledger.events_between(start, limit=max(1, min(int(limit), 2000)))}


@router.get("/reports")
def report_list(limit: int = 20):
    return {"reports": ledger.list_reports(limit)}


@router.post("/reports/daily")
def report_daily():
    return reports.daily()


@router.post("/reports/weekly")
def report_weekly():
    return reports.weekly()


@router.post("/report/ask")
def report_ask():
    """Generate a bounded, traceable report with the local Gemma brain."""
    privacy_mode = os.environ.get(
        "SIMORGH_PRIVACY_MODE",
        str(load_config().get("privacy_mode", "local-only")),
    ).strip().lower() or "local-only"

    if privacy_mode != "local-only":
        raise HTTPException(409, "local report requires privacy_mode=local-only")

    daily = ledger.latest_report("DAILY")
    weekly = ledger.latest_report("WEEKLY")
    post_boot = ledger.latest_report("POST_BOOT")
    latest = ledger.latest_snapshot()
    observation_source = "ledger.latest_snapshot"

    if latest is None:
        latest = observer.capture()
        observation_source = "observer.capture"

    observation_timestamp = latest.get("timestamp") if isinstance(latest, dict) else None
    observation_age_seconds = None

    if observation_timestamp:
        try:
            observed_at = datetime.fromisoformat(observation_timestamp)
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
            observation_age_seconds = (
                datetime.now(timezone.utc) - observed_at
            ).total_seconds()
        except (TypeError, ValueError):
            observation_age_seconds = None

    observation = {
        "source": observation_source,
        "timestamp": observation_timestamp,
        "age_seconds": observation_age_seconds,
    }

    evidence = build_report_evidence(
        latest_snapshot=latest,
        daily=daily,
        weekly=weekly,
        post_boot=post_boot,
        goals=ledger.list_goals(),
        self_model=ledger.list_self_model(),
    )
    evidence["observation"] = observation

    prompt = (
        "این داده‌ها فقط مشاهدهٔ واقعی محلی Mother هستند. "
        "فقط بر اساس همین evidence یک گزارش فارسی روشن و کوتاه بنویس. "
        "وضعیت فعلی، تغییرات مهم، رخدادهای مهم، محدودیت‌های مشاهده و "
        "چند پیشنهاد غیرالزامی برای بهبود را بیان کن. "
        "هرجا داده کافی نیست NOT_AVAILABLE یا تأیید نشده بگو. "
        "هیچ واقعیت تازه‌ای نساز و هیچ دستور اجرایی خودکار نده. "
        "گزارش را در 4 بند کوتاه نگه دار.\n\n"
        + json.dumps(
            evidence,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
    )

    report_system_prompt = (
        "تو راصد محلی SIMORGH MOTHER هستی. "
        "فقط evidence را گزارش کن. "
        "KNOWN و INFERRED را جدا نگه دار. "
        "هیچ واقعیت تازه‌ای نساز."
    )

    response = generate(
        report_system_prompt,
        prompt,
        max_tokens=180,
        needs_quality=True,
        task_class="report",
    )

    if not response:
        raise HTTPException(503, "local model unavailable")

    verification = build_verification(response, evidence)

    try:
        model_review = review_report_with_gemma(response, evidence)
    except Exception as exc:
        model_review = {
            "status": "MODEL_REVIEW_UNAVAILABLE",
            "reason": type(exc).__name__,
        }

    ledger.record_event(
        component="report",
        event_type="gemma_report_generated",
        actor="Gemma",
        action="report",
        severity="info",
        verified=False,
        provenance="local_llm",
        data={
            "evidence_sha256": verification["evidence_sha256"],
            "response_sha256": verification["response_sha256"],
            "model": discover_local_brain().get("model"),
            "model_review_status": model_review.get("status"),
        },
    )

    return {
        "response": response,
        "ai_generated": True,
        "model_mode": "local-only",
        "model": discover_local_brain().get("model"),
        "evidence_scope": "mother_local_state",
        "verification": verification,
        "model_review": model_review,
        "brain": discover_local_brain(),
        "observation": observation,
    }


@router.get("/brain")
def brain():
    return discover_local_brain()


@router.post("/goals")
def create_goal(payload: GoalRequest):
    goal_id = ledger.add_goal(payload.title, payload.target_date, source="human")
    return {"ok": True, "id": goal_id, "goals": ledger.list_goals()}


@router.post("/goals/{goal_id}/status")
def update_goal(goal_id: int, status: str):
    status = status.upper()
    if status not in {"OPEN", "DONE", "BLOCKED", "PAUSED"}:
        raise HTTPException(400, "invalid goal status")
    if not ledger.set_goal_status(goal_id, status):
        raise HTTPException(404, "goal not found")
    return {"ok": True, "goals": ledger.list_goals()}


@router.get("/research/search")
def research_search(q: str):
    if not q.strip():
        raise HTTPException(400, "query is required")
    return {"query": q[:300], "search_urls": browser_search_urls(q)}


@router.post("/research/quarantine")
def research_quarantine(payload: ResearchURLRequest):
    try:
        return fetch_to_quarantine(ledger, payload.url)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        ledger.record_event(
            component="research",
            event_type="quarantine_fetch_failed",
            actor="research_gateway",
            action="fetch",
            severity="error",
            verified=False,
            data={"error": type(exc).__name__, "detail": str(exc)[:1000]},
        )
        raise HTTPException(502, "research fetch failed") from exc


@router.get("/research/quarantine")
def quarantine_list(status: str | None = None):
    return {"items": ledger.list_quarantine(status=status)}


@router.get("/research/quarantine/{item_id}")
def quarantine_get(item_id: int):
    item = ledger.get_quarantine(item_id)
    if not item:
        raise HTTPException(404, "quarantine item not found")
    return item


@router.post("/research/quarantine/{item_id}/ai-review")
def quarantine_ai_review(item_id: int):
    try:
        return advisory_ai_review(ledger, item_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.post("/research/quarantine/{item_id}/approve")
def quarantine_approve(item_id: int, payload: ReviewRequest):
    try:
        return approve_to_memory(ledger, item_id, reviewer="human", note=payload.note)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/research/quarantine/{item_id}/reject")
def quarantine_reject(item_id: int, payload: ReviewRequest):
    try:
        return reject(ledger, item_id, reviewer="human", note=payload.note)
    except (ValueError,) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/coding/propose")
def coding_propose(payload: CodeRepairRequest):
    try:
        return propose_patch(ledger, payload.task, payload.paths)
    except (ValueError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/coding/{repair_id}/verify")
def coding_verify(repair_id: int):
    try:
        return verify_patch(ledger, repair_id)
    except (KeyError, ValueError, OSError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/coding/{repair_id}/apply")
def coding_apply(repair_id: int, payload: ApplyRepairRequest):
    try:
        return apply_verified_patch(ledger, repair_id, payload.approve, payload.note)
    except (KeyError, ValueError, OSError, RuntimeError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/coding")
def coding_list():
    return {"items": ledger.list_code_repairs()}


__all__ = ["router"]
