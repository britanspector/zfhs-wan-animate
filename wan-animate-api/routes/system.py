"""Service discovery and AutoDL public URL routes."""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter

router = APIRouter()

NOTEBOOK_FILENAME = "中升智学动作迁移实验项目教学代码.ipynb"
NOTEBOOK_PATH = f"/jupyter/lab/tree/notebooks/{quote(NOTEBOOK_FILENAME)}"


def _jupyter_token() -> str:
    token = os.environ.get("AutodlAutoPanelToken", "")
    if not token:
        token_file = Path(
            os.environ.get("ZFHS_JUPYTER_TOKEN_FILE", "/root/zfhs-wan-animate/.run/jupyter.token")
        )
        if token_file.is_file():
            token = token_file.read_text(encoding="utf-8").strip()
    return token


def _public_urls() -> dict:
    base_6006 = os.environ.get("AutoDLService6006URL", "").rstrip("/")
    base_6008 = os.environ.get("AutoDLService6008URL", "").rstrip("/")
    if not base_6006:
        base_6006 = "http://127.0.0.1:6006"
    if not base_6008:
        base_6008 = "http://127.0.0.1:6008"

    token = _jupyter_token()
    notebook_base = f"{base_6008}{NOTEBOOK_PATH}"
    notebook_public = f"{notebook_base}?token={token}" if token else notebook_base
    jupyter_lab_public = f"{base_6008}/jupyter/lab?token={token}" if token else f"{base_6008}/jupyter/lab"

    return {
        "comfyui": {
            "port": 6006,
            "local_url": "http://127.0.0.1:6006",
            "public_url": base_6006,
            "template_url": (
                f"{base_6006}/?template=p07_wan22_animate_v4&source=zfhs-workflow-templates"
            ),
        },
        "web": {
            "port": int(os.environ.get("WAN_ANIMATE_API_PORT", "6020")),
            "local_url": f"http://127.0.0.1:{os.environ.get('WAN_ANIMATE_API_PORT', '6020')}",
            "public_url": f"{base_6008}/",
        },
        "notebook": {
            "port": int(os.environ.get("JUPYTER_PORT", "8888")),
            "local_url": "http://127.0.0.1:8888/jupyter/",
            "public_url": notebook_public,
            "jupyter_lab_url": jupyter_lab_public,
            "filename": NOTEBOOK_FILENAME,
        },
        "gateway": {
            "port": 6008,
            "public_url": f"{base_6008}/",
        },
    }


@router.get("/api/services")
def list_services() -> dict:
    return {"ok": True, "services": _public_urls()}


@router.get("/api/external-url-6006")
def external_url_6006() -> dict:
    urls = _public_urls()
    return {"ok": True, "url": urls["comfyui"]["public_url"], "port": 6006}


@router.get("/api/external-url-6008")
def external_url_6008() -> dict:
    urls = _public_urls()
    return {"ok": True, "url": urls["gateway"]["public_url"], "port": 6008}
