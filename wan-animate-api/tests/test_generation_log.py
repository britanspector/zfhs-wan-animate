"""Tests for generation_log service."""

from __future__ import annotations

import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))

from services.generation_log import build_generation_log, format_size_readable, persist_generation_log


def test_format_size_readable():
    assert format_size_readable(500) == "500 B"
    assert "KB" in format_size_readable(2048)
    assert "MB" in format_size_readable(2 * 1024 * 1024)


def test_build_generation_log_v5_includes_advanced_params():
    settings = {
        "workflows": {"v5": {"label": "保身份动作迁移"}},
        "tunables": [
            {"key": "62:pose_strength", "label": "姿态强度"},
            {"key": "62:face_strength", "label": "表情/脸型跟随"},
        ],
    }
    job = {
        "prompt_id": "test-prompt",
        "workflow_variant": "v5",
        "status": "completed",
        "image": "C罗.jpg",
        "video": "世界杯手势舞.mp4",
        "width": 468,
        "height": 832,
        "seconds": 30,
        "tunables": {"62:pose_strength": 0.65, "62:face_strength": 0.1},
        "created_at": "2026-07-03T08:00:00+00:00",
        "updated_at": "2026-07-03T08:05:00+00:00",
    }
    results = [
        {
            "filename": "角色迁移_C罗_世界杯手势舞_00001.mp4",
            "url": "/output/zfhs-wan-animate/角色迁移_C罗_世界杯手势舞_00001.mp4",
            "size_bytes": 12345678,
        }
    ]
    log = build_generation_log(job=job, settings=settings, results=results)
    assert log["工作流"] == "保身份动作迁移"
    assert log["工作流版本"] == "v5"
    assert log["输入"]["角色参考图"] == "C罗.jpg"
    assert log["高级参数"]["姿态强度"] == 0.65
    assert log["输出"][0]["大小可读"]
    assert log["耗时秒"] == 300


def test_build_generation_log_v4_no_advanced_block():
    settings = {"workflows": {"v4": {"label": "标准动作迁移"}}, "tunables": []}
    job = {
        "prompt_id": "p1",
        "workflow_variant": "v4",
        "status": "completed",
        "image": "C罗.jpg",
        "video": "世界杯手势舞.mp4",
        "tunables": {"62:pose_strength": 1.0},
        "created_at": "2026-07-03T08:00:00+00:00",
        "updated_at": "2026-07-03T08:01:00+00:00",
    }
    log = build_generation_log(job=job, settings=settings, results=[])
    assert "高级参数" not in log


def test_persist_generation_log(tmp_path: Path):
    log = {"任务ID": "abc", "状态": "已完成"}
    path = persist_generation_log(tmp_path, "abc", log)
    assert path.is_file()
    assert "abc" in path.name
