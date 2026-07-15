"""Workflow business logic for API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from zfhs_wan_animate.comfy_client import ComfyOutput
from zfhs_wan_animate.runner import (
    interrupt_comfy,
    load_config,
    poll_p07,
    resolve_runtime,
    submit_p07,
)
from zfhs_wan_animate.workflow_p07 import extract_tunable_defaults

from public_urls import (
    build_api_view_path_url,
    normalize_media_url,
    resolve_public_base_url,
)

from .generation_log import build_generation_log, persist_generation_log
from .job_store import JobStore
from .progress_diagnostic import ProgressDiagnosticService

logger = logging.getLogger("wan_animate.workflow")


def _project_root(settings: dict[str, Any]) -> Path:
    return Path(settings["_project_root"])


def _workflow_variants(settings: dict[str, Any]) -> dict[str, dict[str, Any]]:
    variants = settings.get("workflows") or {}
    if variants:
        return variants
    return {
        "v4": {
            "id": settings.get("workflow_id", "P07-animate-v4"),
            "label": "标准动作迁移",
            "description": "",
            "file": settings.get("workflow_path", "workflows/p07_animate_v4.json"),
        }
    }


def _variant_file(settings: dict[str, Any], variant: str) -> Path:
    root = _project_root(settings)
    variants = _workflow_variants(settings)
    if variant not in variants:
        raise KeyError(f"Unknown workflow variant: {variant}")
    rel = variants[variant]["file"]
    path = Path(rel)
    return path if path.is_absolute() else root / path


def _input_dir(settings: dict[str, Any]) -> Path:
    return Path(settings["comfy_root"]) / "input"


def _resolve_basename(name: str) -> str:
    return Path(name).name


class WorkflowService:
    def __init__(
        self,
        settings: dict[str, Any],
        job_store: JobStore,
        progress_diagnostic: ProgressDiagnosticService | None = None,
    ):
        self.settings = settings
        self.job_store = job_store
        self.cfg = load_config(settings["_project_root"] / "config" / "default.yaml")
        data_dir = Path(settings["jobs_path"]).parent
        self.progress_diagnostic = progress_diagnostic or ProgressDiagnosticService(
            data_dir, settings["comfy_url"]
        )

    def list_workflows(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for key, meta in _workflow_variants(self.settings).items():
            out.append(
                {
                    "variant": key,
                    "id": meta.get("id", key),
                    "name": meta.get("label", key),
                    "description": meta.get("description", ""),
                    "workflow_file": meta.get("file"),
                }
            )
        return out

    def get_config(self, workflow_id: str | None = None, request: Any | None = None) -> dict[str, Any]:
        variants_cfg = _workflow_variants(self.settings)
        default_variant = self.settings.get("default_workflow_variant", "v4")
        tunable_key_list = [str(t["key"]) for t in self.settings.get("tunables", []) if t.get("key")]
        variants: list[dict[str, Any]] = []
        for key, meta in variants_cfg.items():
            wf_path = _variant_file(self.settings, key)
            variants.append(
                {
                    "variant": key,
                    "id": meta.get("id", key),
                    "label": meta.get("label", key),
                    "description": meta.get("description", ""),
                    "file": str(meta.get("file")),
                    "default_tunables": extract_tunable_defaults(wf_path, tunable_key_list)
                    if wf_path.is_file()
                    else {},
                }
            )

        if workflow_id and workflow_id not in {v["variant"] for v in variants} and workflow_id not in {
            v["id"] for v in variants
        }:
            if workflow_id not in ("default", "P07-动作迁移-Wan2.2AnimateV4", "P07-animate-v4"):
                raise KeyError(f"Unknown workflow: {workflow_id}")

        defaults = self.settings.get("defaults", {})
        samples = self.settings.get("samples", {})
        public_base = resolve_public_base_url(self.settings, request)
        image_name = Path(samples["image"]).name if samples.get("image") else "C罗.jpg"
        video_name = Path(samples["video"]).name if samples.get("video") else "世界杯手势舞.mp4"
        legacy_id = variants_cfg.get(default_variant, {}).get("id", "P07-animate-v4")
        return {
            "workflow_id": legacy_id,
            "default_workflow_variant": default_variant,
            "variants": variants,
            "tunables": self.settings.get("tunables", []),
            "save_node_id": self.settings.get("output_node_id", "867"),
            "fps": self.settings.get("fps", 30),
            "defaults": {
                "width": defaults.get("width", 468),
                "height": defaults.get("height", 832),
                "seconds": defaults.get("seconds", 30),
            },
            "duration_options": [
                {"label": "10 秒内", "seconds": 10, "frames": 300},
                {"label": "20 秒内", "seconds": 20, "frames": 600},
                {"label": "30 秒内", "seconds": 30, "frames": 900},
            ],
            "input_fields": [
                {"key": "57:image", "description": "角色参考图"},
                {"key": "997:video", "description": "动作参考视频（含音轨）"},
                {"key": "1001:value", "description": "宽度"},
                {"key": "1002:value", "description": "高度"},
                {"key": "1003:value", "description": "最大帧数"},
            ],
            "samples": {
                "image": samples.get("image"),
                "video": samples.get("video"),
                "image_preview_url": build_api_view_path_url(public_base, image_name, "input"),
                "video_preview_url": build_api_view_path_url(public_base, video_name, "input"),
            },
        }

    def validate_input(self, image: str, video: str) -> dict[str, Any]:
        image_base = _resolve_basename(image)
        video_base = _resolve_basename(video)
        input_dir = _input_dir(self.settings)
        missing: list[str] = []
        if not (input_dir / image_base).is_file():
            missing.append(f"角色参考图不存在：{image_base}")
        if not (input_dir / video_base).is_file():
            missing.append(f"动作参考视频不存在：{video_base}")
        if missing:
            raise ValueError("；".join(missing))
        return {"ok": True, "image": image_base, "video": video_base}

    def generate(
        self,
        *,
        workflow_id: str | None = None,
        workflow_variant: str | None = None,
        input_values: dict[str, object] | None = None,
        tunables: dict[str, object] | None = None,
        workflow_template: dict | None = None,
        client_id: str | None = None,
        image_name: str | None = None,
        video_name: str | None = None,
        width: int | None = None,
        height: int | None = None,
        seconds: int | None = None,
    ) -> dict[str, Any]:
        variant = workflow_variant or self.settings.get("default_workflow_variant", "v4")
        variants = _workflow_variants(self.settings)
        if variant not in variants:
            raise KeyError(f"Unknown workflow variant: {variant}")

        wf_path = _variant_file(self.settings, variant)
        rt = resolve_runtime(self.cfg, workflow_path=wf_path)
        merged_input = dict(input_values or {})
        if tunables:
            merged_input.update(tunables)

        parsed = _parse_input_values(merged_input)
        image = _resolve_basename(image_name or parsed.get("image") or "")
        video = _resolve_basename(video_name or parsed.get("video") or "")
        w = width if width is not None else parsed.get("width", rt["width"])
        h = height if height is not None else parsed.get("height", rt["height"])
        sec = seconds if seconds is not None else parsed.get("seconds", rt["seconds"])

        if workflow_template is None and (not image or not video):
            raise ValueError("57:image and 997:video are required in input_values")

        if workflow_template is None:
            validated = self.validate_input(image, video)
            image = validated["image"]
            video = validated["video"]
            merged_input["57:image"] = image
            merged_input["997:video"] = video

        logger.info(
            "generate submit variant=%s client_id=%s image=%s video=%s",
            variant,
            client_id,
            image,
            video,
        )

        submit = submit_p07(
            image_name=image or "",
            video_name=video or "",
            width=w,
            height=h,
            seconds=sec,
            client_id=client_id,
            input_values=None if workflow_template else merged_input,
            workflow_template=workflow_template,
            config=self.cfg,
            workflow_path=wf_path,
        )

        variant_meta = variants[variant]
        self.job_store.create(
            prompt_id=submit.prompt_id,
            workflow_id=variant_meta.get("id", variant),
            workflow_variant=variant,
            client_id=submit.client_id,
            image=image,
            video=video,
            width=w,
            height=h,
            seconds=sec,
            input_values=merged_input,
            tunables=tunables or {},
            prompt_snapshot=submit.prompt,
        )

        self.progress_diagnostic.start(
            prompt_id=submit.prompt_id,
            client_id=submit.client_id,
            prompt_snapshot=submit.prompt,
            meta={
                "workflow_variant": variant,
                "image": image,
                "video": video,
            },
        )

        return {
            "success": True,
            "prompt_id": submit.prompt_id,
            "client_id": submit.client_id,
            "workflow_variant": variant,
            "number": 1,
            "prompt_snapshot": submit.prompt,
            "resolved_image": image,
            "resolved_video": video,
        }

    def append_diagnostic_frontend(self, prompt_id: str, entries: list[dict[str, Any]]) -> None:
        self.progress_diagnostic.append_frontend(prompt_id, entries)

    def progress(self, prompt_id: str) -> dict[str, Any]:
        return self.progress_diagnostic.get_progress(prompt_id)

    def result(self, prompt_id: str, request: Any | None = None) -> dict[str, Any]:
        job = self.job_store.get(prompt_id)
        ref_video = None
        if job and job.get("video"):
            ref_video = Path(self.settings["comfy_root"]) / "input" / Path(job["video"]).name
            if not ref_video.is_file():
                ref_video = Path(job["video"]) if Path(job["video"]).is_file() else None

        polled = poll_p07(prompt_id, config=self.cfg, ref_video_path=ref_video)
        public_base = resolve_public_base_url(self.settings, request)

        if polled.error:
            self.job_store.update(prompt_id, status="failed", error=polled.error)
            self.progress_diagnostic.finish(prompt_id, status="failed", extra={"error": polled.error})
            return {
                "success": True,
                "pending": False,
                "prompt_id": prompt_id,
                "error": polled.error,
                "results": [],
            }

        if polled.pending:
            self.job_store.update(prompt_id, status="running")
            return {
                "success": True,
                "pending": True,
                "prompt_id": prompt_id,
                "results": [],
            }

        results = [
            _output_to_result(out, public_base, comfy_root=Path(self.settings["comfy_root"]))
            for out in polled.outputs
        ]
        updated_job = self.job_store.update(prompt_id, status="completed", results=results)
        self.progress_diagnostic.finish(prompt_id, status="completed")

        if updated_job:
            gen_log = build_generation_log(
                job=updated_job,
                settings=self.settings,
                results=results,
                public_base=public_base,
            )
            data_dir = Path(self.settings["jobs_path"]).parent
            persist_generation_log(data_dir, prompt_id, gen_log)
            self.job_store.update(prompt_id, generation_log=gen_log)

        return {
            "success": True,
            "pending": False,
            "prompt_id": prompt_id,
            "results": results,
        }

    def interrupt(self) -> dict[str, Any]:
        interrupt_comfy(config=self.cfg)
        for job in self.job_store.list_recent(20):
            if job.get("status") in {"queued", "running"}:
                pid = job["prompt_id"]
                self.job_store.update(pid, status="interrupted")
                self.progress_diagnostic.finish(pid, status="interrupted")
        return {"success": True}

    def history(self, limit: int = 50, request: Any | None = None) -> list[dict[str, Any]]:
        public_base = resolve_public_base_url(self.settings, request)
        jobs = self.job_store.list_recent(limit)
        normalized: list[dict[str, Any]] = []
        for job in jobs:
            copy = dict(job)
            results = copy.get("results") or []
            copy["results"] = [
                {
                    **r,
                    "url": normalize_media_url(r.get("url", ""), public_base),
                    "view_url": normalize_media_url(r.get("view_url", ""), public_base),
                }
                for r in results
            ]
            normalized.append(copy)
        return normalized


def _parse_input_values(input_values: dict[str, object]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if "57:image" in input_values:
        out["image"] = str(input_values["57:image"])
    if "997:video" in input_values:
        out["video"] = str(input_values["997:video"])
    if "1001:value" in input_values:
        out["width"] = int(input_values["1001:value"])
    if "1002:value" in input_values:
        out["height"] = int(input_values["1002:value"])
    if "seconds" in input_values:
        out["seconds"] = int(input_values["seconds"])
    elif "1003:value" in input_values:
        frames = int(input_values["1003:value"])
        out["seconds"] = max(1, frames // 30)
    return out


def _output_to_result(
    out: ComfyOutput,
    public_base: str,
    *,
    comfy_root: Path,
) -> dict[str, Any]:
    result = {
        "type": "video",
        "filename": out.filename,
        "subfolder": out.subfolder,
        "url": out.output_url(public_base),
        "view_url": build_api_view_path_url(public_base, out.filename, "output", out.subfolder),
    }
    file_path = comfy_root / "output" / (out.subfolder or "") / out.filename
    if file_path.is_file():
        result["size_bytes"] = file_path.stat().st_size
    return result
