"""User-facing generation summary JSON with Chinese labels."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def format_size_readable(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def _tunable_labels(settings: dict[str, Any]) -> dict[str, str]:
    return {
        str(t["key"]): str(t.get("label") or t["key"])
        for t in settings.get("tunables", [])
        if t.get("key")
    }


def _workflow_label(settings: dict[str, Any], variant: str | None) -> str:
    workflows = settings.get("workflows") or {}
    if variant and variant in workflows:
        return str(workflows[variant].get("label") or variant)
    return str(variant or "unknown")


def _elapsed_seconds(job: dict[str, Any]) -> int | None:
    created = job.get("created_at")
    updated = job.get("updated_at")
    if not created or not updated:
        return None
    try:
        t0 = datetime.fromisoformat(str(created))
        t1 = datetime.fromisoformat(str(updated))
        return max(0, int((t1 - t0).total_seconds()))
    except ValueError:
        return None


def build_generation_log(
    *,
    job: dict[str, Any],
    settings: dict[str, Any],
    results: list[dict[str, Any]],
    public_base: str = "",
) -> dict[str, Any]:
    variant = job.get("workflow_variant") or "v4"
    tunables = job.get("tunables") or {}
    labels = _tunable_labels(settings)

    log: dict[str, Any] = {
        "工作流": _workflow_label(settings, variant),
        "工作流版本": variant,
        "任务ID": job.get("prompt_id"),
        "状态": _status_label(job.get("status")),
        "创建时间": job.get("created_at"),
        "完成时间": job.get("updated_at"),
        "输入": {
            "角色参考图": job.get("image") or job.get("input_values", {}).get("57:image"),
            "动作参考视频": job.get("video") or job.get("input_values", {}).get("997:video"),
            "宽度": job.get("width"),
            "高度": job.get("height"),
            "时长秒": job.get("seconds"),
        },
        "输出": [],
    }

    elapsed = _elapsed_seconds(job)
    if elapsed is not None:
        log["耗时秒"] = elapsed

    if variant == "v5" and tunables:
        advanced: dict[str, Any] = {}
        for key, value in tunables.items():
            advanced[labels.get(key, key)] = value
        log["高级参数"] = advanced

    for r in results:
        size_bytes = r.get("size_bytes")
        item: dict[str, Any] = {
            "文件名": r.get("filename"),
            "访问地址": r.get("url") or r.get("view_url"),
        }
        if size_bytes is not None:
            item["大小字节"] = size_bytes
            item["大小可读"] = format_size_readable(int(size_bytes))
        log["输出"].append(item)

    return log


def _status_label(status: str | None) -> str:
    mapping = {
        "queued": "排队中",
        "running": "运行中",
        "completed": "已完成",
        "failed": "失败",
        "interrupted": "已中断",
    }
    return mapping.get(str(status or ""), str(status or "未知"))


def persist_generation_log(data_dir: Path, prompt_id: str, log: dict[str, Any]) -> Path:
    out_dir = Path(data_dir) / "generation_logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{prompt_id}.json"
    path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
