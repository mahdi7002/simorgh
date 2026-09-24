from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .ai_work_log import ACTORS, AIWorkLog
from .ledger import MotherLedger

router = APIRouter(prefix="/api/mother", tags=["mother-ai-work-log"])
_work_log: AIWorkLog | None = None


def get_work_log() -> AIWorkLog:
    global _work_log
    if _work_log is None:
        _work_log = AIWorkLog(MotherLedger())
    return _work_log


class AIWorkLogRequest(BaseModel):
    actor: str
    model: str | None = Field(default=None, max_length=500)
    repo: str | None = Field(default=None, max_length=1000)
    ref: str | None = Field(default=None, max_length=200)
    action: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    reason: str | None = Field(default=None, max_length=4000)
    evidence: str = Field(min_length=1, max_length=12000)


@router.post("/ai-work-log")
def create_ai_work_log(payload: AIWorkLogRequest):
    if payload.actor not in ACTORS:
        raise HTTPException(400, f"actor must be one of: {', '.join(ACTORS)}")
    try:
        entry_id = get_work_log().record(
            actor=payload.actor,
            model=payload.model,
            repo=payload.repo,
            ref=payload.ref,
            action=payload.action,
            summary=payload.summary,
            reason=payload.reason,
            evidence=payload.evidence,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return {"ok": True, "id": entry_id, "verification": "claimed"}


@router.get("/ai-work-log/report")
def ai_work_log_report():
    return get_work_log().report()


__all__ = ["router", "get_work_log"]
