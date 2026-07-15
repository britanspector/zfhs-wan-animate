"""Warmup status routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from services.warmup_status import get_warmup_status

router = APIRouter()


@router.get("/api/warmup/status")
def warmup_status(request: Request) -> dict:
    comfy = request.app.state.comfy_manager.status()
    return get_warmup_status(
        comfy_running=bool(comfy.get("running")),
        settings=request.app.state.settings,
    )
