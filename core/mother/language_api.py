from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from .bilingual_activity import (
    activity_path,
    latest_path,
    load_policy,
    save_policy,
)

router = APIRouter(
    prefix="/api/mother",
    tags=["language"],
)


class LanguagePolicyRequest(BaseModel):
    system_language: Literal["fa", "en"] | None = None
    interaction_language: Literal["fa", "en", "auto"] | None = None
    audience: Literal[
        "child",
        "simple",
        "normal",
        "technical",
    ] | None = None


@router.get("/language")
def get_language_policy():
    policy = load_policy()

    return {
        "policy": policy,
        "bilingual_storage": True,
        "languages": ["fa", "en"],
        "activity_file": str(activity_path()),
        "latest_file": str(latest_path()),
    }


@router.post("/language")
def update_language_policy(
    payload: LanguagePolicyRequest,
):
    policy = save_policy(
        system_language=payload.system_language,
        interaction_language=payload.interaction_language,
        audience=payload.audience,
    )

    return {
        "ok": True,
        "policy": policy,
    }
