"""P07 workflow loading and patching."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_FPS = 30
NODE_IMAGE = "57"
NODE_VIDEO = "997"
NODE_WIDTH = "1001"
NODE_HEIGHT = "1002"
NODE_FRAMES = "1003"
NODE_OUTPUT = "867"

TUNABLE_KEYS: tuple[tuple[str, str], ...] = (
    ("62", "pose_strength"),
    ("62", "face_strength"),
    ("996", "draw_head"),
    ("64", "crop_position"),
    ("27", "steps"),
    ("27", "denoise_strength"),
    ("171", "strength_0"),
    ("171", "strength_1"),
    ("171", "strength_2"),
    ("171", "strength_3"),
    ("171", "strength_4"),
    ("65", "positive_prompt"),
    ("65", "negative_prompt"),
)


def tunable_key(node_id: str, field: str) -> str:
    return f"{node_id}:{field}"


def parse_tunable_key_list(keys: list[str]) -> list[tuple[str, str]]:
    parsed: list[tuple[str, str]] = []
    for key in keys:
        if ":" not in key:
            continue
        node_id, field = key.split(":", 1)
        parsed.append((node_id, field))
    return parsed


def extract_tunable_defaults(
    workflow_path: Path,
    tunable_keys: list[str] | None = None,
) -> dict[str, object]:
    data = load_workflow(workflow_path)
    pairs = parse_tunable_key_list(tunable_keys) if tunable_keys else list(TUNABLE_KEYS)
    out: dict[str, object] = {}
    for node_id, field in pairs:
        if node_id not in data:
            continue
        inputs = data[node_id].get("inputs", {})
        if field in inputs and not isinstance(inputs[field], list):
            out[tunable_key(node_id, field)] = inputs[field]
    return out


def build_prompt_with_tunables(
    *,
    image_name: str,
    video_name: str,
    width: int = 468,
    height: int = 832,
    seconds: int = 30,
    workflow_path: Path,
    fps: int = DEFAULT_FPS,
    tunables: dict[str, object] | None = None,
    trim_to_audio: bool = False,
) -> dict:
    data = load_workflow(workflow_path)
    values: dict[str, object] = {
        tunable_key(NODE_IMAGE, "image"): image_name,
        tunable_key(NODE_VIDEO, "video"): video_name,
        tunable_key(NODE_WIDTH, "value"): width,
        tunable_key(NODE_HEIGHT, "value"): height,
        "seconds": seconds,
    }
    if tunables:
        values.update(tunables)
    apply_input_values(data, values, fps=fps)
    ensure_audio_wiring(data, trim_to_audio=trim_to_audio)
    return data


def load_workflow(workflow_path: Path) -> dict:
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    data.pop("_api_config", None)
    return data


def ensure_audio_wiring(data: dict, *, trim_to_audio: bool = False) -> None:
    if NODE_OUTPUT not in data:
        raise KeyError(f"Workflow missing output node {NODE_OUTPUT}")
    inputs = data[NODE_OUTPUT].setdefault("inputs", {})
    inputs["audio"] = [NODE_VIDEO, 2]
    inputs["format"] = "video/h264-mp4"
    inputs["trim_to_audio"] = trim_to_audio


def build_prompt(
    *,
    image_name: str,
    video_name: str,
    width: int = 468,
    height: int = 832,
    seconds: int = 30,
    workflow_path: Path,
    fps: int = DEFAULT_FPS,
    trim_to_audio: bool = False,
) -> dict:
    data = load_workflow(workflow_path)
    _patch_node(data, NODE_IMAGE, "image", image_name)
    _patch_node(data, NODE_VIDEO, "video", video_name)
    _patch_node(data, NODE_WIDTH, "value", width)
    _patch_node(data, NODE_HEIGHT, "value", height)
    _patch_node(data, NODE_FRAMES, "value", max(1, seconds * fps))
    ensure_audio_wiring(data, trim_to_audio=trim_to_audio)
    return data


def apply_input_values(data: dict, input_values: dict[str, object], *, fps: int = DEFAULT_FPS) -> dict:
    """Apply zealman-style input_values keys like '57:image' or '1003:value'."""
    seconds: int | None = None
    for key, value in input_values.items():
        if ":" not in key:
            if key == "seconds":
                seconds = int(value)
            continue
        node_id, field = key.split(":", 1)
        if node_id == "996" and field == "draw_head" and isinstance(value, bool):
            value = "True" if value else "False"
        if node_id == NODE_FRAMES and field == "value" and seconds is None:
            _patch_node(data, node_id, field, int(value))
        else:
            _patch_node(data, node_id, field, value)
    if seconds is not None:
        _patch_node(data, NODE_FRAMES, "value", max(1, seconds * fps))
    ensure_audio_wiring(data)
    return data


def _patch_node(data: dict, node_id: str, field: str, value) -> None:
    if node_id not in data:
        raise KeyError(f"Workflow missing node {node_id}")
    inputs = data[node_id].get("inputs")
    if not isinstance(inputs, dict):
        raise KeyError(f"Node {node_id} has no inputs dict")
    inputs[field] = value
