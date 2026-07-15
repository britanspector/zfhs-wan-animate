"""Tests for ComfyUI warmup helpers."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import warmup_comfy  # noqa: E402


def test_detect_milestone_node_508_finished():
    msg = {
        "type": "progress_state",
        "data": {
            "prompt_id": "pid-1",
            "nodes": {
                "508": {"state": "finished", "value": 482, "max": 482},
            },
        },
    }
    assert warmup_comfy.detect_milestone(msg) == "node_508_finished"


def test_detect_milestone_node_27_started_from_progress_state():
    msg = {
        "type": "progress_state",
        "data": {
            "nodes": {
                "27": {"state": "running", "value": 12, "max": 1427},
            },
        },
    }
    assert warmup_comfy.detect_milestone(msg) == "node_27_started"


def test_detect_milestone_node_27_started_from_progress():
    msg = {
        "type": "progress",
        "data": {"node": "27", "value": 5, "max": 1427},
    }
    assert warmup_comfy.detect_milestone(msg) == "node_27_started"


def test_detect_milestone_ignores_idle_node_27():
    msg = {
        "type": "progress_state",
        "data": {
            "nodes": {
                "27": {"state": "running", "value": 0, "max": 1427},
            },
        },
    }
    assert warmup_comfy.detect_milestone(msg) is None


def test_should_skip_warmup_env():
    assert warmup_comfy.should_skip_warmup(
        skip_env=True,
        state={"comfy_pid": 1, "milestone": "node_508_finished"},
        current_comfy_pid=1,
    )


def test_should_skip_warmup_matching_pid():
    assert warmup_comfy.should_skip_warmup(
        skip_env=False,
        state={"comfy_pid": 42, "milestone": "node_508_finished"},
        current_comfy_pid=42,
    )


def test_should_not_skip_warmup_pid_mismatch():
    assert not warmup_comfy.should_skip_warmup(
        skip_env=False,
        state={"comfy_pid": 42, "milestone": "node_508_finished"},
        current_comfy_pid=99,
    )


def test_should_not_skip_warmup_without_milestone():
    assert not warmup_comfy.should_skip_warmup(
        skip_env=False,
        state={"comfy_pid": 42, "milestone": ""},
        current_comfy_pid=42,
    )


def test_write_and_read_warmup_state(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("WAN_ANIMATE_DATA_DIR", str(tmp_path))
    cfg = {"_project_root": PROJECT_ROOT}
    warmup_comfy.write_warmup_state(
        cfg,
        comfy_pid=7,
        milestone="node_27_started",
        elapsed_seconds=120,
        prompt_id="abc",
    )
    state = warmup_comfy.read_warmup_state(cfg)
    assert state is not None
    assert state["comfy_pid"] == 7
    assert state["milestone"] == "node_27_started"
    assert state["prompt_id"] == "abc"
    raw = json.loads((tmp_path / ".warmup_state.json").read_text(encoding="utf-8"))
    assert raw["elapsed_seconds"] == 120


def test_module_has_single_run_warmup_async():
    source = inspect.getsource(warmup_comfy)
    assert source.count("async def run_warmup_async") == 1


def test_submit_warmup_job_calls_submit_p07(tmp_path: Path, monkeypatch):
    comfy_root = tmp_path / "ComfyUI"
    input_dir = comfy_root / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "C罗.jpg").write_bytes(b"img")
    (input_dir / "世界杯手势舞.mp4").write_bytes(b"vid")

    cfg = {
        "_project_root": PROJECT_ROOT,
        "comfy_root": str(comfy_root),
        "default_workflow_variant": "v4",
        "workflows": {
            "v4": {"file": "workflows/p07_animate_v4.json"},
        },
        "defaults": {"width": 468, "height": 832},
        "samples": {
            "image": str(input_dir / "C罗.jpg"),
            "video": str(input_dir / "世界杯手势舞.mp4"),
        },
    }
    fake_result = MagicMock(prompt_id="warmup-pid", client_id="warmup-cid")

    with patch.object(warmup_comfy, "submit_p07", return_value=fake_result) as mock_submit:
        result = warmup_comfy.submit_warmup_job(cfg, "warmup-test-client")

    assert result is fake_result
    mock_submit.assert_called_once()
    kwargs = mock_submit.call_args.kwargs
    assert kwargs["client_id"] == "warmup-test-client"
    assert kwargs["input_values"]["1003:value"] == warmup_comfy.WARMUP_FRAMES
    assert kwargs["seconds"] == 10
