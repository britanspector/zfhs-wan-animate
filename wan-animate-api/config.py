"""API configuration."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))


def load_settings() -> dict:
    path = Path(os.environ.get("ZFHS_CONFIG_PATH", PROJECT_ROOT / "config" / "default.yaml"))
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    local = PROJECT_ROOT / "config" / "local.yaml"
    if local.is_file() and os.environ.get("ZFHS_CONFIG_PATH") is None:
        with local.open(encoding="utf-8") as f:
            local_cfg = yaml.safe_load(f) or {}
        for key, value in local_cfg.items():
            if isinstance(value, dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(value)
            else:
                cfg[key] = value
    cfg["_project_root"] = PROJECT_ROOT
    cfg["comfy_url"] = os.environ.get("COMFYUI_URL", cfg.get("comfy_url", "http://127.0.0.1:6006"))
    cfg["comfy_root"] = os.environ.get("COMFYUI_ROOT", cfg.get("comfy_root", "/app/ComfyUI"))
    start_script = os.environ.get("COMFY_START_SCRIPT", cfg.get("comfy_start_script", ""))
    if start_script and not Path(start_script).is_absolute():
        start_script = str((PROJECT_ROOT / start_script).resolve())
    cfg["comfy_start_script"] = start_script
    api = cfg.setdefault("api", {})
    api["host"] = os.environ.get("WAN_ANIMATE_API_HOST", api.get("host", "0.0.0.0"))
    api["port"] = int(os.environ.get("WAN_ANIMATE_API_PORT", api.get("port", 6020)))
    api["base_url"] = os.environ.get("WAN_ANIMATE_API_BASE_URL", api.get("base_url", f"http://127.0.0.1:{api['port']}"))
    jobs_default = Path(os.environ.get("WAN_ANIMATE_DATA_DIR", "/app/data")) / "jobs.json"
    if not os.environ.get("WAN_ANIMATE_DATA_DIR") and (PROJECT_ROOT / "wan-animate-api" / "data").is_dir():
        jobs_default = PROJECT_ROOT / "wan-animate-api" / "data" / "jobs.json"
    cfg["jobs_path"] = Path(os.environ.get("WAN_ANIMATE_JOBS_PATH", jobs_default))
    return cfg
