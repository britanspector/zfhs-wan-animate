"""Tests for input validation."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(API_DIR.parent / "src"))

from services.job_store import JobStore
from services.progress_diagnostic import ProgressDiagnosticService
from services.workflow_service import WorkflowService


def _service(tmp_path: Path, comfy_root: Path) -> WorkflowService:
    settings = {
        "_project_root": API_DIR.parent,
        "comfy_root": str(comfy_root),
        "comfy_url": "http://127.0.0.1:6006",
        "jobs_path": tmp_path / "jobs.json",
        "workflows": {
            "v4": {"id": "P07-animate-v4", "label": "标准", "file": "workflows/p07_animate_v4.json"},
        },
        "default_workflow_variant": "v4",
        "tunables": [],
    }
    store = JobStore(settings["jobs_path"])
    diag = ProgressDiagnosticService(tmp_path, settings["comfy_url"])
    return WorkflowService(settings, store, diag)


def test_validate_input_ok(tmp_path: Path):
    comfy_root = tmp_path / "ComfyUI"
    input_dir = comfy_root / "input"
    input_dir.mkdir(parents=True)
    (input_dir / "C罗.jpg").write_bytes(b"img")
    (input_dir / "世界杯手势舞.mp4").write_bytes(b"vid")

    svc = _service(tmp_path, comfy_root)
    result = svc.validate_input("C罗.jpg", "世界杯手势舞.mp4")
    assert result["ok"] is True
    assert result["image"] == "C罗.jpg"


def test_validate_input_missing(tmp_path: Path):
    comfy_root = tmp_path / "ComfyUI"
    (comfy_root / "input").mkdir(parents=True)

    svc = _service(tmp_path, comfy_root)
    try:
        svc.validate_input("missing.jpg", "世界杯手势舞.mp4")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "不存在" in str(exc)


def test_progress_diagnostic_writes_files(tmp_path: Path):
    store = JobStore(tmp_path / "jobs.json")
    diag = ProgressDiagnosticService(tmp_path, "http://127.0.0.1:6006", store)
    diag.start(
        prompt_id="pid-1",
        client_id="cid-1",
        prompt_snapshot={"1": {"class_type": "Test"}},
        meta={"image": "C罗.jpg"},
    )
    diag.log_backend_event(
        "cid-1",
        '{"type": "executing", "data": {"node": "1", "prompt_id": "pid-1"}}',
    )
    diag.append_frontend("pid-1", [{"event": "ws_open", "detail": {}}])
    diag.finish("pid-1", status="completed")

    run_dirs = list((tmp_path / "diagnostic_logs").rglob("pid-1"))
    assert run_dirs
    run_dir = run_dirs[0]
    assert (run_dir / "meta.json").is_file()
    assert (run_dir / "frontend.jsonl").is_file()
    assert (run_dir / "backend.jsonl").is_file()
    backend_lines = (run_dir / "backend.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(backend_lines) == 1
    assert '"type": "executing"' in backend_lines[0]


def test_progress_diagnostic_no_tracker_thread(tmp_path: Path):
    diag = ProgressDiagnosticService(tmp_path, "http://127.0.0.1:6006")
    diag.start(
        prompt_id="pid-2",
        client_id="cid-2",
        prompt_snapshot={"1": {"class_type": "Test"}},
    )
    assert not hasattr(diag, "_trackers")
