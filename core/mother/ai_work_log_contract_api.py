from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .ai_work_log_contract import record_claimed, list_report

router = APIRouter(prefix="/api/mother", tags=["mother-ai-work-log"])


class AIWorkLogIn(BaseModel):
    actor: str = Field(min_length=2, max_length=50)
    model: str | None = Field(default=None, max_length=200)
    repo: str | None = Field(default=None, max_length=1000)
    ref: str | None = Field(default=None, max_length=200)
    action: str = Field(min_length=2, max_length=200)
    summary: str = Field(min_length=3, max_length=5000)
    reason: str | None = Field(default=None, max_length=5000)
    evidence: str | None = Field(default=None, max_length=10000)


@router.post("/ai-work-log-v1")
def create_ai_work_log(payload: AIWorkLogIn):
    try:
        row_id = record_claimed(
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

    return {
        "ok": True,
        "id": row_id,
        "verification": "claimed",
        "verified_by": None,
        "note": (
            "POST only records a claim. It cannot set verification=verified. "
            "Mother changes verification only after reproducible git evidence "
            "and pytest exit 0."
        ),
    }


@router.get("/ai-work-log-v1")
def get_ai_work_log(actor: str | None = None):
    return list_report(actor=actor)
