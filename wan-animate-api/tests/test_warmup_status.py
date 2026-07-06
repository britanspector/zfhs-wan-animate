"""Tests for warmup status service."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

API_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = API_DIR.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))

import warmup_comfy  # noqa: E402
from services.warmup_status import (  # noqa: E402
    WARMUP_LOCK_FILE,
    get_warmup_status,
    warmup_process_running,
)


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    monkeypatch.setenv("WAN_ANIMATE_DATA_DIR", str(data_dir))
    return {"_project_root": PROJECT_ROOT}


def test_skipped_env_ready(monkeypatch, cfg):
    monkeypatch.setenv("SKIP_WARMUP", "1")
    status = get_warmup_status(comfy_running=False, settings=cfg)
    assert status["ready"] is True
    assert status["warming"] is False
    assert status["skipped"] is True


def test_comfy_not_running_not_warming(cfg):
    status = get_warmup_status(comfy_running=False, settings=cfg)
    assert status["ready"] is False
    assert status["warming"] is False
    assert status["skipped"] is False


def test_pid_match_ready(tmp_path: Path, cfg, monkeypatch):
    monkeypatch.delenv("SKIP_WARMUP", raising=False)
    warmup_comfy.write_warmup_state(
        cfg,
        comfy_pid=42,
        milestone="node_508_finished",
        elapsed_seconds=90,
        prompt_id="p1",
    )
    with patch("services.warmup_status.read_comfy_pid", return_value=42):
        status = get_warmup_status(comfy_running=True, settings=cfg)
    assert status["ready"] is True
    assert status["warming"] is False


def test_pid_mismatch_warming(tmp_path: Path, cfg, monkeypatch):
    monkeypatch.delenv("SKIP_WARMUP", raising=False)
    warmup_comfy.write_warmup_state(
        cfg,
        comfy_pid=41,
        milestone="node_508_finished",
        elapsed_seconds=90,
        prompt_id="p1",
    )
    with patch("services.warmup_status.read_comfy_pid", return_value=42):
        status = get_warmup_status(comfy_running=True, settings=cfg)
    assert status["ready"] is False
    assert status["warming"] is True


def test_warmup_lock_running(tmp_path: Path, monkeypatch):
    lock = tmp_path / "warmup.lock"
    lock.write_text("99999", encoding="utf-8")
    monkeypatch.setattr("services.warmup_status.WARMUP_LOCK_FILE", lock)

    with patch("services.warmup_status.os.kill", return_value=None):
        assert warmup_process_running() is True

    with patch("services.warmup_status.os.kill", side_effect=OSError):
        assert warmup_process_running() is False


def test_warmup_status_endpoint(client, cfg, monkeypatch):
    monkeypatch.delenv("SKIP_WARMUP", raising=False)
    warmup_comfy.write_warmup_state(
        cfg,
        comfy_pid=7,
        milestone="node_27_started",
        elapsed_seconds=120,
        prompt_id="p2",
    )
    with patch("services.warmup_status.read_comfy_pid", return_value=7):
        with patch.object(
            client.app.state.comfy_manager,
            "status",
            return_value={"running": True, "starting": False, "reason": "ok"},
        ):
            resp = client.get("/api/warmup/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["milestone"] == "node_27_started"


@pytest.fixture
def client(cfg, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("WAN_ANIMATE_DATA_DIR", str(Path(cfg["_project_root"]) / "wan-animate-api" / "data"))
    from app import app

    app.state.settings = cfg
    return TestClient(app)
