from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .coding import apply_verified_patch, propose_patch, verify_patch
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
        "quarantine": ledger.list_quarantine(limit=20),
        "code_repairs": ledger.list_code_repairs(limit=20),
    }


@router.get("/reports")
def report_list(limit: int = 20):
    return {"reports": ledger.list_reports(limit)}


@router.post("/reports/daily")
def report_daily():
    return reports.daily()


@router.post("/reports/weekly")
def report_weekly():
    return reports.weekly()


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
