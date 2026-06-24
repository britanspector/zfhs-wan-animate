"""Parse ComfyUI history status messages into human-readable errors."""

from __future__ import annotations

import ast
import re
from typing import Any


def parse_comfy_execution_error(messages: Any) -> str | None:
    """Extract a concise error from ComfyUI ``status.messages``."""
    if not messages:
        return None

    items = messages
    if isinstance(messages, str):
        try:
            items = ast.literal_eval(messages)
        except (SyntaxError, ValueError):
            return _shorten(messages)

    if not isinstance(items, list):
        return _shorten(str(messages))

    for item in items:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        event, payload = item[0], item[1]
        if event != "execution_error" or not isinstance(payload, dict):
            continue
        node_type = payload.get("node_type") or payload.get("node_id") or "unknown"
        node_id = payload.get("node_id")
        label = f"{node_type}" + (f" (节点 {node_id})" if node_id else "")
        raw = str(payload.get("exception_message") or payload.get("exception_type") or "未知错误")
        return f"{label}: {_normalize_onnx_message(raw)}"

    return _shorten(str(messages))


def _normalize_onnx_message(msg: str) -> str:
    msg = re.sub(r"\s+", " ", msg).strip()
    if "CUDNN_STATUS_SUBLIBRARY_VERSION_MISMATCH" in msg:
        return (
            "ONNX CUDA/cuDNN 版本不匹配。"
            "请通过 zealman 启动脚本重启 ComfyUI，确保 cuDNN 库路径正确。"
        )
    if "Failed to allocate memory for requested buffer of size" in msg:
        m = re.search(r"size (\d+)", msg)
        if m and int(m.group(1)) > 10**12:
            return (
                "ONNX 在 GPU 上推理异常（多为 cuDNN 路径或损坏的 ONNX 会话）。"
                "请重试；若仍失败请通过面板脚本重启 ComfyUI。"
            )
        return "ONNX 显存不足，请降低分辨率/时长或重启 ComfyUI 后重试。"
    if len(msg) > 320:
        return msg[:317] + "..."
    return msg


def _shorten(text: str, limit: int = 320) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."
