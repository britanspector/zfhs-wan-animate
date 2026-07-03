"""Per-run diagnostic progress logs (backend ComfyUI WS events + frontend UI snapshots)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zfhs_wan_animate.comfy_progress import ComfyProgressTracker


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProgressDiagnosticService:
    def __init__(self, data_dir: Path, comfy_url: str) -> None:
        self.data_dir = Path(data_dir)
        self.comfy_url = comfy_url
        self._trackers: dict[str, ComfyProgressTracker] = {}
        self._lock = threading.Lock()

    def _run_dir(self, prompt_id: str) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.data_dir / "diagnostic_logs" / day / prompt_id

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def start(
        self,
        *,
        prompt_id: str,
        client_id: str,
        prompt_snapshot: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> None:
        run_dir = self._run_dir(prompt_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        meta_path = run_dir / "meta.json"
        payload = {
            "prompt_id": prompt_id,
            "client_id": client_id,
            "started_at": _now_iso(),
            "comfy_url": self.comfy_url,
            **(meta or {}),
        }
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        backend_log = run_dir / "backend.jsonl"

        def _on_raw(msg_type: str, data: dict[str, Any]) -> None:
            self._append_jsonl(
                backend_log,
                {
                    "ts": _now_iso(),
                    "source": "comfy_ws",
                    "type": msg_type,
                    "data": data,
                },
            )

        tracker = ComfyProgressTracker(
            self.comfy_url,
            client_id,
            prompt_id,
            prompt_snapshot,
            on_raw_message=_on_raw,
        )
        tracker.start()
        with self._lock:
            self._trackers[prompt_id] = tracker

    def append_frontend(self, prompt_id: str, entries: list[dict[str, Any]]) -> None:
        if not entries:
            return
        run_dir = self._run_dir(prompt_id)
        frontend_log = run_dir / "frontend.jsonl"
        for entry in entries:
            self._append_jsonl(
                frontend_log,
                {
                    "ts": entry.get("ts") or _now_iso(),
                    "source": "frontend",
                    **{k: v for k, v in entry.items() if k != "ts"},
                },
            )

    def finish(self, prompt_id: str, *, status: str, extra: dict[str, Any] | None = None) -> None:
        with self._lock:
            tracker = self._trackers.pop(prompt_id, None)
        if tracker:
            tracker.stop()

        run_dir = self._run_dir(prompt_id)
        meta_path = run_dir / "meta.json"
        meta: dict[str, Any] = {}
        if meta_path.is_file():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                meta = {}
        meta["finished_at"] = _now_iso()
        meta["status"] = status
        if extra:
            meta.update(extra)
        run_dir.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
