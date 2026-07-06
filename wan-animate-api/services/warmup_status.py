"""Warmup readiness for the web UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import warmup_comfy  # noqa: E402

WARMUP_LOCK_FILE = Path("/tmp/zfhs-wan-animate-warmup.lock")
COMFY_PID_FILE = PROJECT_ROOT / ".run" / "comfyui.pid"


def _skip_warmup_env() -> bool:
    return os.environ.get("SKIP_WARMUP", "").strip().lower() in {"1", "true", "yes"}


def read_comfy_pid() -> int | None:
    if not COMFY_PID_FILE.is_file():
        return None
    try:
        return int(COMFY_PID_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return None


def warmup_process_running() -> bool:
    if not WARMUP_LOCK_FILE.is_file():
        return False
    try:
        pid = int(WARMUP_LOCK_FILE.read_text(encoding="utf-8").strip())
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def get_warmup_status(*, comfy_running: bool, settings: dict[str, Any]) -> dict[str, Any]:
    skipped = _skip_warmup_env()
    comfy_pid = read_comfy_pid()
    state = warmup_comfy.read_warmup_state(settings)
    milestone = state.get("milestone") if state else None
    warmup_running = warmup_process_running()

    if skipped:
        return {
            "ready": True,
            "warming": False,
            "skipped": True,
            "milestone": milestone,
            "comfy_pid": comfy_pid,
            "warmup_running": warmup_running,
        }

    if not comfy_running:
        return {
            "ready": False,
            "warming": False,
            "skipped": False,
            "milestone": milestone,
            "comfy_pid": comfy_pid,
            "warmup_running": warmup_running,
        }

    ready = warmup_comfy.should_skip_warmup(
        skip_env=False,
        state=state,
        current_comfy_pid=comfy_pid,
    )
    return {
        "ready": ready,
        "warming": not ready,
        "skipped": False,
        "milestone": milestone,
        "comfy_pid": comfy_pid,
        "warmup_running": warmup_running,
    }
