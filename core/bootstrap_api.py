"""First-run API surface for the local SIMORGH web application."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.hardware import probe
from core.model_manager import installed_models, install_model, recommend_models, register_local_model
from core.user_runtime import runtime_snapshot, save_config

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


class RuntimeConfigRequest(BaseModel):
    display_name: str = Field(default="", max_length=120)
    privacy_mode: str = Field(default="local-only", max_length=40)


@router.get("")
def bootstrap():
    profile = probe()
    return {
        "runtime": runtime_snapshot(),
        "hardware": profile.to_dict(),
        "models": recommend_models(profile),
        "installed_models": installed_models(),
        "knowledge": {
            "database_first": True,
            "requires_model": False,
            "offline_capable": True,
        },
    }


@router.post("/configure")
def configure(payload: RuntimeConfigRequest):
    config = save_config(
        {
            "configured": True,
            "display_name": payload.display_name.strip(),
            "privacy_mode": "local-only",
        }
    )
    return {"ok": True, "config": config, "runtime": runtime_snapshot()}


@router.post("/models/{model_id}/install")
def install(model_id: str):
    try:
        return {"ok": True, "model": install_model(model_id)}
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/models/import")
def import_model(path: str):
    try:
        return {"ok": True, "model": register_local_model(path)}
    except (FileNotFoundError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


__all__ = ["router"]
