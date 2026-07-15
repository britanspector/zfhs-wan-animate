#!/usr/bin/env python3
"""Background ComfyUI warmup: submit a short workflow and interrupt after key milestones."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zfhs_wan_animate.runner import interrupt_comfy, load_config, submit_p07  # noqa: E402

WARMUP_FRAMES = 300
DEFAULT_TIMEOUT = 600


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(msg: str) -> None:
    print(f"[warmup] {msg}", flush=True)


def data_dir(cfg: dict[str, Any]) -> Path:
    env = os.environ.get("WAN_ANIMATE_DATA_DIR")
    if env:
        return Path(env)
    jobs_path = os.environ.get("WAN_ANIMATE_JOBS_PATH")
    if jobs_path:
        return Path(jobs_path).parent
    return PROJECT_ROOT / "wan-animate-api" / "data"


def warmup_state_path(cfg: dict[str, Any]) -> Path:
    return data_dir(cfg) / ".warmup_state.json"


def read_warmup_state(cfg: dict[str, Any]) -> dict[str, Any] | None:
    path = warmup_state_path(cfg)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_warmup_state(
    cfg: dict[str, Any],
    *,
    comfy_pid: int | None,
    milestone: str,
    elapsed_seconds: int,
    prompt_id: str | None = None,
) -> None:
    path = warmup_state_path(cfg)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "comfy_pid": comfy_pid,
        "completed_at": _now_iso(),
        "milestone": milestone,
        "elapsed_seconds": elapsed_seconds,
        "prompt_id": prompt_id,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def should_skip_warmup(
    *,
    skip_env: bool,
    state: dict[str, Any] | None,
    current_comfy_pid: int | None,
) -> bool:
    if skip_env:
        return True
    if not state or not state.get("milestone"):
        return False
    if current_comfy_pid is None:
        return False
    return state.get("comfy_pid") == current_comfy_pid


def resolve_workflow_path(cfg: dict[str, Any]) -> Path:
    root = Path(cfg["_project_root"])
    variants = cfg.get("workflows") or {}
    variant = cfg.get("default_workflow_variant", "v4")
    if variant not in variants:
        rel = cfg.get("workflow_path", "workflows/p07_animate_v4.json")
        path = Path(rel)
        return path if path.is_absolute() else root / path
    rel = variants[variant]["file"]
    path = Path(rel)
    return path if path.is_absolute() else root / path


def sample_names(cfg: dict[str, Any]) -> tuple[str, str]:
    samples = cfg.get("samples") or {}
    image = Path(samples.get("image", "C罗.jpg")).name
    video = Path(samples.get("video", "世界杯手势舞.mp4")).name
    return image, video


def validate_samples(cfg: dict[str, Any]) -> tuple[str, str]:
    image, video = sample_names(cfg)
    comfy_root = Path(cfg.get("comfy_root", "/app/ComfyUI"))
    input_dir = comfy_root / "input"
    missing = [name for name in (image, video) if not (input_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"预热素材不存在于 {input_dir}: {', '.join(missing)}")
    return image, video


def comfy_ws_url(comfy_url: str, client_id: str) -> str:
    parsed = urlparse(comfy_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    return urlunparse((scheme, netloc, "/ws", "", f"clientId={client_id}", ""))


def detect_milestone(msg: dict[str, Any]) -> str | None:
    msg_type = msg.get("type")
    data = msg.get("data") or {}
    if not isinstance(data, dict):
        return None

    if msg_type == "progress_state":
        nodes = data.get("nodes") or {}
        if not isinstance(nodes, dict):
            return None
        node508 = nodes.get("508") or {}
        if node508.get("state") == "finished":
            return "node_508_finished"
        node27 = nodes.get("27") or {}
        value = node27.get("value") or 0
        if node27.get("state") == "running" and value > 0:
            return "node_27_started"

    if msg_type == "progress":
        if str(data.get("node")) == "27" and (data.get("value") or 0) > 0:
            return "node_27_started"

    return None


def submit_warmup_job(cfg: dict[str, Any], client_id: str):
    image, video = validate_samples(cfg)
    defaults = cfg.get("defaults", {})
    wf_path = resolve_workflow_path(cfg)
    return submit_p07(
        image_name=image,
        video_name=video,
        width=int(defaults.get("width", 468)),
        height=int(defaults.get("height", 832)),
        seconds=10,
        client_id=client_id,
        input_values={
            "57:image": image,
            "997:video": video,
            "1001:value": int(defaults.get("width", 468)),
            "1002:value": int(defaults.get("height", 832)),
            "1003:value": WARMUP_FRAMES,
        },
        config=cfg,
        workflow_path=wf_path,
    )


async def run_warmup_async(cfg: dict[str, Any], *, timeout: float) -> tuple[str, str]:
    import websockets

    client_id = f"warmup-{uuid4().hex}"
    comfy_url = cfg.get("comfy_url", "http://127.0.0.1:6006")
    ws_url = comfy_ws_url(comfy_url, client_id)
    deadline = time.monotonic() + timeout
    prompt_id = ""
    milestone = "timeout"

    async with websockets.connect(ws_url, open_timeout=15) as ws:

        async def do_submit() -> str:
            submit = await asyncio.to_thread(submit_warmup_job, cfg, client_id)
            _log(f"submitted prompt_id={submit.prompt_id} client_id={client_id}")
            return submit.prompt_id

        submit_task = asyncio.create_task(do_submit())

        while time.monotonic() < deadline:
            if submit_task.done() and submit_task.exception() is not None:
                raise submit_task.exception()  # type: ignore[misc]

            if not prompt_id and submit_task.done():
                prompt_id = submit_task.result()

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=min(5.0, remaining))
            except asyncio.TimeoutError:
                continue
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="ignore")
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            data = msg.get("data") or {}
            if prompt_id and data.get("prompt_id") and data.get("prompt_id") != prompt_id:
                continue
            hit = detect_milestone(msg)
            if hit:
                milestone = hit
                break

        if not submit_task.done():
            prompt_id = await submit_task
        elif not prompt_id:
            prompt_id = submit_task.result()

    _log(f"milestone={milestone}")
    await asyncio.to_thread(interrupt_comfy, config=cfg)
    _log("interrupted comfy queue")
    return milestone, prompt_id


def run_warmup(cfg: dict[str, Any], *, timeout: float, comfy_pid: int | None) -> int:
    start = time.monotonic()
    prompt_id: str | None = None
    try:
        milestone, prompt_id = asyncio.run(run_warmup_async(cfg, timeout=timeout))
    except Exception as exc:
        _log(f"ERROR: {exc}")
        try:
            interrupt_comfy(config=cfg)
        except Exception:
            pass
        return 1

    elapsed = int(time.monotonic() - start)
    write_warmup_state(
        cfg,
        comfy_pid=comfy_pid,
        milestone=milestone,
        elapsed_seconds=elapsed,
        prompt_id=prompt_id,
    )
    _log(f"done milestone={milestone} elapsed={elapsed}s")
    return 0 if milestone != "timeout" else 2


def dry_run(cfg: dict[str, Any]) -> int:
    image, video = validate_samples(cfg)
    wf_path = resolve_workflow_path(cfg)
    comfy_url = cfg.get("comfy_url", "http://127.0.0.1:6006")
    import httpx

    r = httpx.get(f"{comfy_url.rstrip('/')}/system_stats", timeout=10)
    r.raise_for_status()
    _log(f"ok samples={image},{video} workflow={wf_path.name} comfy={comfy_url}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Warm up ComfyUI models after instance start")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--comfy-pid", type=int, default=None)
    parser.add_argument("--force", action="store_true", help="Run even if warmup state matches pid")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg = load_config()

    if os.environ.get("SKIP_WARMUP", "").strip() in {"1", "true", "yes"}:
        _log("SKIP_WARMUP=1, exiting")
        return 0

    comfy_pid = args.comfy_pid
    if comfy_pid is None:
        pid_file = PROJECT_ROOT / ".run" / "comfyui.pid"
        if pid_file.is_file():
            try:
                comfy_pid = int(pid_file.read_text(encoding="utf-8").strip())
            except ValueError:
                comfy_pid = None

    if not args.force and should_skip_warmup(
        skip_env=False,
        state=read_warmup_state(cfg),
        current_comfy_pid=comfy_pid,
    ):
        _log(f"skipped (comfy_pid={comfy_pid} already warmed)")
        return 0

    if args.dry_run:
        return dry_run(cfg)

    return run_warmup(cfg, timeout=args.timeout, comfy_pid=comfy_pid)


if __name__ == "__main__":
    raise SystemExit(main())
