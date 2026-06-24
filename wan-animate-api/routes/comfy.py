"""ComfyUI proxy routes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from zfhs_wan_animate.comfy_client import ComfyClient

router = APIRouter()


def _client(request: Request) -> ComfyClient:
    settings = request.app.state.settings
    return ComfyClient(settings["comfy_url"], comfy_root=Path(settings["comfy_root"]))


@router.get("/api/comfy/status")
def comfy_status(request: Request) -> dict[str, Any]:
    return request.app.state.comfy_manager.status()


@router.post("/api/comfy/start")
def comfy_start(request: Request) -> dict[str, Any]:
    return request.app.state.comfy_manager.start()


@router.post("/api/comfy/stop")
def comfy_stop(request: Request) -> dict[str, Any]:
    return request.app.state.comfy_manager.stop()


@router.post("/api/comfy/proxy/interrupt")
def comfy_interrupt(request: Request) -> dict[str, Any]:
    return request.app.state.workflow_service.interrupt()


@router.get("/api/comfy/proxy/history")
def comfy_history(request: Request, prompt_id: str | None = Query(default=None)) -> dict[str, Any]:
    with _client(request) as client:
        if prompt_id:
            entry = client.get_history_entry(prompt_id)
            return {prompt_id: entry} if entry else {}
        return client.get_history()


@router.post("/api/comfy/upload/file")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    overwrite: bool = True,
) -> dict[str, Any]:
    content = await file.read()
    filename = file.filename or "upload.bin"
    with _client(request) as client:
        try:
            return client.upload_file_bytes(filename, content, overwrite=overwrite)
        except Exception as exc:
            # fallback copy to input
            dest = Path(request.app.state.settings["comfy_root"]) / "input" / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(content)
            return {"name": filename, "subfolder": "", "type": "input", "fallback": "copy"}


@router.get("/api/comfy/view")
def comfy_view(
    request: Request,
    filename: str = Query(...),
    type: str = Query(default="input", alias="type"),
    subfolder: str = Query(default=""),
) -> Response:
    with _client(request) as client:
        try:
            resp = client.fetch_view(filename=filename, file_type=type, subfolder=subfolder)
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "application/octet-stream"))
        except Exception as exc:
            root = Path(request.app.state.settings["comfy_root"])
            folder = "input" if type == "input" else "output"
            local = root / folder / subfolder / filename if subfolder else root / folder / filename
            if not local.is_file():
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            return StreamingResponse(local.open("rb"))


@router.get("/api/comfy/queue")
def comfy_queue(request: Request) -> dict[str, Any]:
    with _client(request) as client:
        return client.get_queue()
