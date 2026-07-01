"""Workflow API routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

router = APIRouter()


class GenerateBody(BaseModel):
    workflow_id: str | None = None
    workflow_variant: str | None = "v4"
    input_values: dict[str, Any] | None = None
    tunables: dict[str, Any] | None = None
    workflow_template: dict[str, Any] | None = None
    client_id: str | None = None


@router.get("/api/workflow/list")
def workflow_list(request: Request) -> list[dict[str, Any]]:
    return request.app.state.workflow_service.list_workflows()


@router.get("/api/workflow/config/{workflow_id}")
def workflow_config(workflow_id: str, request: Request) -> dict[str, Any]:
    try:
        return request.app.state.workflow_service.get_config(workflow_id, request=request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/workflow/generate")
def workflow_generate(body: GenerateBody, request: Request) -> dict[str, Any]:
    try:
        return request.app.state.workflow_service.generate(
            workflow_id=body.workflow_id,
            workflow_variant=body.workflow_variant,
            input_values=body.input_values,
            tunables=body.tunables,
            workflow_template=body.workflow_template,
            client_id=body.client_id,
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/api/workflow/result")
def workflow_result(request: Request, prompt_id: str = Query(...)) -> dict[str, Any]:
    return request.app.state.workflow_service.result(prompt_id, request=request)


@router.get("/api/workflow/history")
def workflow_history(request: Request, limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    jobs = request.app.state.workflow_service.history(limit=limit, request=request)
    return {"success": True, "jobs": jobs}
