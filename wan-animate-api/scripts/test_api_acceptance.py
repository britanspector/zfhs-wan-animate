#!/usr/bin/env python3
"""Backend API acceptance tests (no full generation wait)."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from zfhs_wan_animate.audio_mux import has_audio_stream  # noqa: E402

API_BASE = "http://127.0.0.1:6020"
COMFY_BASE = "http://127.0.0.1:6006"
WORKFLOW_ID = "P07-animate-v4"


def load_samples() -> dict:
    with (PROJECT_ROOT / "config" / "default.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)["samples"]


def assert_true(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)
    print(f"  OK {msg}")


def main() -> int:
    samples = load_samples()
    image_path = Path(samples["image"])
    video_path = Path(samples["video"])
    client = httpx.Client(base_url=API_BASE, timeout=120.0)

    print("=== wan-animate-api acceptance ===\n")

    # 1 health
    r = client.get("/api/health")
    assert_true(r.status_code == 200 and r.json().get("ok"), "health")

    # 2 comfy status / start
    r = client.get("/api/comfy/status")
    st = r.json()
    if not st.get("running"):
        r = client.post("/api/comfy/start")
        assert_true(r.json().get("success"), "comfy start")
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            st = client.get("/api/comfy/status").json()
            if st.get("running"):
                break
            time.sleep(2)
    assert_true(client.get("/api/comfy/status").json().get("running"), "comfy running")

    # 3 init params
    r = client.get(f"/api/workflow/config/{WORKFLOW_ID}")
    cfg = r.json()
    assert_true(r.status_code == 200, "workflow config status")
    assert_true(cfg["defaults"]["width"] == 468, "default width")
    assert_true(cfg["defaults"]["height"] == 832, "default height")
    assert_true(len(cfg["duration_options"]) == 3, "duration options")
    assert_true(len(cfg.get("variants", [])) >= 2, "workflow variants v4/v5")
    assert_true(len(cfg.get("tunables", [])) >= 5, "tunable schema")

    # 4 upload image
    with image_path.open("rb") as f:
        r = client.post(
            "/api/comfy/upload/file",
            files={"file": (image_path.name, f, "image/png")},
            data={"overwrite": "true"},
        )
    img = r.json()
    assert_true(r.status_code == 200 and img.get("name"), "upload image")

    # 5 upload video
    with video_path.open("rb") as f:
        r = client.post(
            "/api/comfy/upload/file",
            files={"file": (video_path.name, f, "video/mp4")},
            data={"overwrite": "true"},
        )
    vid = r.json()
    assert_true(r.status_code == 200 and vid.get("name"), "upload video")
    assert_true(has_audio_stream(video_path), "reference video has audio")

    # 6 preview
    r = client.get("/api/comfy/view", params={"filename": img["name"], "type": "input"})
    assert_true(r.status_code == 200, "preview input")

    # 7 generate
    input_values = {
        "57:image": img["name"],
        "997:video": vid["name"],
        "1001:value": 468,
        "1002:value": 832,
        "1003:value": 300,
    }
    r = client.post(
        "/api/workflow/generate",
        json={"workflow_id": WORKFLOW_ID, "input_values": input_values, "client_id": "acceptance-test"},
    )
    gen = r.json()
    assert_true(r.status_code == 200 and gen.get("success"), "generate")
    prompt_id = gen["prompt_id"]
    snap = gen.get("prompt_snapshot", {})
    assert_true(snap["1001"]["inputs"]["value"] == 468, "patched width")
    assert_true(snap["1002"]["inputs"]["value"] == 832, "patched height")
    assert_true(snap["1003"]["inputs"]["value"] == 300, "patched frames")
    assert_true(snap["867"]["inputs"]["audio"] == ["997", 2], "audio wiring")

    # queue non-empty
    time.sleep(1)
    q = httpx.get(f"{COMFY_BASE}/queue", timeout=10).json()
    pending = q.get("queue_pending", [])
    running = q.get("queue_running", [])
    assert_true(bool(pending or running), "comfy queue has task")

    # 8 result pending
    r = client.get("/api/workflow/result", params={"prompt_id": prompt_id})
    res = r.json()
    assert_true(res.get("pending") is True, "result pending")

    # 9 history
    r = client.get("/api/workflow/history")
    jobs = r.json().get("jobs", [])
    assert_true(any(j.get("prompt_id") == prompt_id for j in jobs), "history contains job")

    # 10 interrupt
    r = client.post("/api/comfy/proxy/interrupt")
    assert_true(r.json().get("success"), "interrupt")
    time.sleep(2)

    print("\nAll acceptance checks passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nFAIL: {exc}", file=sys.stderr)
        raise
