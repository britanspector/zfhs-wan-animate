"""Health and GPU routes."""

from __future__ import annotations

import subprocess

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
def health() -> dict:
    return {"ok": True, "service": "wan-animate-api"}


@router.get("/api/gpu/info")
def gpu_info() -> dict:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            check=True,
        )
        name = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
        return {"hasGPU": bool(name), "gpuName": name, "isRTX5090": "5090" in name}
    except Exception:
        return {"hasGPU": False, "gpuName": "", "isRTX5090": False}
