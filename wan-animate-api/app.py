"""wan-animate-api FastAPI application."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parent
WEB_DIST = PROJECT_ROOT / "wan-animate-web" / "dist"
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(API_DIR))

from config import load_settings  # noqa: E402
from routes import comfy, health, system, workflow, ws  # noqa: E402
from services.comfy_manager import ComfyManager  # noqa: E402
from services.job_store import JobStore  # noqa: E402
from services.workflow_service import WorkflowService  # noqa: E402

settings = load_settings()

app = FastAPI(title="wan-animate-api", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.settings = settings
app.state.job_store = JobStore(settings["jobs_path"])
app.state.comfy_manager = ComfyManager(
    comfy_url=settings["comfy_url"],
    comfy_root=Path(settings["comfy_root"]),
    start_script=settings.get("comfy_start_script", ""),
    stop_port=int(settings.get("comfy_stop_port", 6006)),
)
app.state.workflow_service = WorkflowService(settings, app.state.job_store)

app.include_router(health.router)
app.include_router(system.router)
app.include_router(comfy.router)
app.include_router(workflow.router)
app.include_router(ws.router)

output_root = Path(settings["comfy_root"]) / "output"
output_root.mkdir(parents=True, exist_ok=True)


@app.get("/output/{subfolder}/{filename}")
def serve_output(subfolder: str, filename: str):
    path = output_root / subfolder / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(path)


if WEB_DIST.is_dir() and (WEB_DIST / "index.html").is_file():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/")
    def serve_spa():
        return FileResponse(WEB_DIST / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("output/"):
            raise HTTPException(status_code=404)
        candidate = WEB_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIST / "index.html")


def create_app() -> FastAPI:
    return app
