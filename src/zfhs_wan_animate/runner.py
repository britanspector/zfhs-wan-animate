"""Orchestrate P07 generation against ComfyUI."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from zfhs_wan_animate.audio_mux import has_audio_stream, mux_reference_audio
from zfhs_wan_animate.comfy_client import ComfyClient, ComfyOutput
from zfhs_wan_animate.comfy_errors import parse_comfy_execution_error
from zfhs_wan_animate.workflow_p07 import apply_input_values, build_prompt, load_workflow


@dataclass
class RunResult:
    prompt_id: str
    elapsed_seconds: float
    outputs: list[ComfyOutput]
    comfy_root: Path

    def primary_output(self) -> ComfyOutput | None:
        return self.outputs[0] if self.outputs else None


@dataclass
class PollResult:
    pending: bool
    prompt_id: str
    outputs: list[ComfyOutput] = field(default_factory=list)
    error: str | None = None
    history: dict[str, Any] | None = None


@dataclass
class SubmitResult:
    prompt_id: str
    client_id: str
    prompt: dict[str, Any]


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    import os

    root = _project_root()
    path = config_path or Path(os.environ.get("ZFHS_CONFIG_PATH", root / "config" / "default.yaml"))
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    local = root / "config" / "local.yaml"
    if local.is_file() and config_path is None and os.environ.get("ZFHS_CONFIG_PATH") is None:
        with local.open(encoding="utf-8") as f:
            local_cfg = yaml.safe_load(f) or {}
        for key, value in local_cfg.items():
            if isinstance(value, dict) and isinstance(cfg.get(key), dict):
                cfg[key].update(value)
            else:
                cfg[key] = value
    cfg["_project_root"] = root
    return cfg


def resolve_runtime(cfg: dict[str, Any], **overrides) -> dict[str, Any]:
    root = Path(cfg["_project_root"])
    defaults = cfg.get("defaults", {})
    wf = overrides.get("workflow_path") or Path(
        _env_or(cfg, "workflow_path", "ZFHS_WORKFLOW_PATH", relative_to=root)
    )
    if not wf.is_absolute():
        wf = root / wf
    return {
        "url": overrides.get("comfy_url") or _env_or(cfg, "comfy_url", "COMFYUI_URL"),
        "comfy_root": Path(overrides.get("comfy_root") or _env_or(cfg, "comfy_root", "COMFYUI_ROOT")),
        "workflow_path": wf,
        "output_node_id": str(overrides.get("output_node_id") or cfg.get("output_node_id", "867")),
        "fps": int(overrides.get("fps") or cfg.get("fps", 30)),
        "width": int(overrides.get("width") if overrides.get("width") is not None else defaults.get("width", 468)),
        "height": int(overrides.get("height") if overrides.get("height") is not None else defaults.get("height", 832)),
        "seconds": int(overrides.get("seconds") if overrides.get("seconds") is not None else defaults.get("seconds", 30)),
        "poll_interval": float(overrides.get("poll_interval") or cfg.get("poll_interval_seconds", 2)),
        "timeout": float(overrides.get("timeout") or cfg.get("timeout_seconds", 1200)),
        "audio_fallback": bool(cfg.get("audio_fallback_enabled", True)),
        "api_base_url": cfg.get("api", {}).get("base_url", ""),
    }


def build_prompt_from_request(
    *,
    workflow_path: Path,
    image_name: str | None = None,
    video_name: str | None = None,
    width: int = 468,
    height: int = 832,
    seconds: int = 30,
    fps: int = 30,
    input_values: dict[str, object] | None = None,
    workflow_template: dict | None = None,
    trim_to_audio: bool = False,
) -> dict:
    if workflow_template is not None:
        data = dict(workflow_template)
        data.pop("_api_config", None)
        if input_values:
            apply_input_values(data, input_values, fps=fps)
        return data
    if input_values:
        data = load_workflow(workflow_path)
        apply_input_values(data, input_values, fps=fps)
        if image_name:
            data["57"]["inputs"]["image"] = image_name
        if video_name:
            data["997"]["inputs"]["video"] = video_name
        return data
    if not image_name or not video_name:
        raise ValueError("image_name and video_name are required without workflow_template")
    return build_prompt(
        image_name=image_name,
        video_name=video_name,
        width=width,
        height=height,
        seconds=seconds,
        workflow_path=workflow_path,
        fps=fps,
        trim_to_audio=trim_to_audio,
    )


def submit_p07(
    *,
    image_name: str,
    video_name: str,
    width: int | None = None,
    height: int | None = None,
    seconds: int | None = None,
    client_id: str | None = None,
    input_values: dict[str, object] | None = None,
    workflow_template: dict | None = None,
    config: dict[str, Any] | None = None,
    **overrides,
) -> SubmitResult:
    cfg = config or load_config()
    rt = resolve_runtime(cfg, **overrides)
    prompt = build_prompt_from_request(
        workflow_path=rt["workflow_path"],
        image_name=image_name,
        video_name=video_name,
        width=width if width is not None else rt["width"],
        height=height if height is not None else rt["height"],
        seconds=seconds if seconds is not None else rt["seconds"],
        fps=rt["fps"],
        input_values=input_values,
        workflow_template=workflow_template,
    )
    cid = client_id or __import__("uuid").uuid4().hex
    with ComfyClient(rt["url"], comfy_root=rt["comfy_root"]) as client:
        client.check_ready()
        prompt_id = client.queue_prompt(prompt, client_id=cid)
    return SubmitResult(prompt_id=prompt_id, client_id=cid, prompt=prompt)


def poll_p07(
    prompt_id: str,
    *,
    config: dict[str, Any] | None = None,
    ref_video_path: Path | None = None,
    **overrides,
) -> PollResult:
    cfg = config or load_config()
    rt = resolve_runtime(cfg, **overrides)
    with ComfyClient(rt["url"], comfy_root=rt["comfy_root"]) as client:
        history = client.get_history_entry(prompt_id)
        if not history:
            return PollResult(pending=True, prompt_id=prompt_id)
        status = history.get("status", {})
        if status.get("status_str") == "error":
            messages = status.get("messages", [])
            parsed = parse_comfy_execution_error(messages)
            return PollResult(
                pending=False,
                prompt_id=prompt_id,
                error=parsed or str(messages),
                history=history,
            )
        outputs = client.resolve_outputs(history, node_id=rt["output_node_id"])
        if outputs:
            outputs = _apply_audio_fallback(outputs, rt["comfy_root"], ref_video_path, rt["audio_fallback"])
            return PollResult(pending=False, prompt_id=prompt_id, outputs=outputs, history=history)
        if status.get("completed"):
            return PollResult(pending=False, prompt_id=prompt_id, outputs=[], history=history)
        return PollResult(pending=True, prompt_id=prompt_id, history=history)


def interrupt_comfy(*, config: dict[str, Any] | None = None, **overrides) -> None:
    cfg = config or load_config()
    rt = resolve_runtime(cfg, **overrides)
    with ComfyClient(rt["url"], comfy_root=rt["comfy_root"]) as client:
        client.interrupt()


def run_p07(
    *,
    image_path: Path,
    video_path: Path,
    width: int | None = None,
    height: int | None = None,
    seconds: int | None = None,
    comfy_url: str | None = None,
    comfy_root: Path | None = None,
    workflow_path: Path | None = None,
    output_node_id: str = "867",
    poll_interval: float = 2.0,
    timeout: float = 1200.0,
    config: dict[str, Any] | None = None,
) -> RunResult:
    cfg = config or load_config()
    rt = resolve_runtime(
        cfg,
        comfy_url=comfy_url,
        comfy_root=comfy_root,
        workflow_path=workflow_path,
        output_node_id=output_node_id,
        width=width,
        height=height,
        seconds=seconds,
        poll_interval=poll_interval,
        timeout=timeout,
    )

    image_path = Path(image_path)
    video_path = Path(video_path)

    started = time.monotonic()
    with ComfyClient(rt["url"], comfy_root=rt["comfy_root"]) as client:
        client.check_ready()
        image_name = client.upload_image(image_path)
        video_name = client.upload_video(video_path)
        prompt = build_prompt(
            image_name=image_name,
            video_name=video_name,
            width=rt["width"],
            height=rt["height"],
            seconds=rt["seconds"],
            workflow_path=rt["workflow_path"],
            fps=rt["fps"],
        )
        prompt_id = client.queue_prompt(prompt)
        history = client.wait_for_completion(
            prompt_id,
            poll_interval=rt["poll_interval"],
            timeout=rt["timeout"],
        )
        outputs = client.resolve_outputs(history, node_id=rt["output_node_id"])
        outputs = _apply_audio_fallback(outputs, rt["comfy_root"], video_path, rt["audio_fallback"])

    elapsed = time.monotonic() - started
    return RunResult(
        prompt_id=prompt_id,
        elapsed_seconds=elapsed,
        outputs=outputs,
        comfy_root=rt["comfy_root"],
    )


def _apply_audio_fallback(
    outputs: list[ComfyOutput],
    comfy_root: Path,
    ref_video: Path | None,
    enabled: bool,
) -> list[ComfyOutput]:
    if not enabled or not ref_video or not outputs:
        return outputs
    ref_video = Path(ref_video)
    if not has_audio_stream(ref_video):
        return outputs

    updated: list[ComfyOutput] = []
    for out in outputs:
        local = out.local_path(comfy_root)
        if not local.is_file():
            updated.append(out)
            continue
        if has_audio_stream(local):
            updated.append(out)
            continue
        muxed = mux_reference_audio(local, ref_video)
        updated.append(
            ComfyOutput(
                filename=muxed.name,
                subfolder=out.subfolder,
                file_type=out.file_type,
                format=out.format,
                base_url=out.base_url,
            )
        )
    return updated


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _env_or(cfg: dict, key: str, env_key: str, *, relative_to: Path | None = None) -> str:
    import os

    val = os.environ.get(env_key)
    if val:
        return val
    val = cfg.get(key)
    if val is None:
        raise KeyError(f"Missing config key {key} and env {env_key}")
    if relative_to and not Path(val).is_absolute():
        return str(relative_to / val)
    return str(val)
