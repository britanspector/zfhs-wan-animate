"""Per-run diagnostic progress logs (backend ComfyUI WS events + frontend UI snapshots)."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from zfhs_wan_animate.comfy_progress import ComfyProgressTracker, ProgressState

if TYPE_CHECKING:
    from .job_store import JobStore

logger = logging.getLogger("wan_animate.progress_diagnostic")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_to_dict(state: ProgressState, *, status: str = "running") -> dict[str, Any]:
    return {
        "workflow_progress": float(state.workflow_progress),
        "node_progress": float(state.node_progress),
        "current_node_name": state.current_node_name or "",
        "executed_nodes": int(state.executed_nodes),
        "total_nodes": int(state.total_nodes),
        "elapsed_seconds": int(state.elapsed_seconds),
        "status": status,
    }


class ProgressDiagnosticService:
    def __init__(
        self,
        data_dir: Path,
        comfy_url: str,
        job_store: JobStore | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.comfy_url = comfy_url
        self.job_store = job_store
        self._client_prompt: dict[str, str] = {}
        self._latest: dict[str, dict[str, Any]] = {}
        self._trackers: dict[str, ComfyProgressTracker] = {}
        self._lock = threading.Lock()

    def _run_dir(self, prompt_id: str) -> Path:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self.data_dir / "diagnostic_logs" / day / prompt_id

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _resolve_prompt_id(self, client_id: str) -> str | None:
        with self._lock:
            prompt_id = self._client_prompt.get(client_id)
        if prompt_id:
            return prompt_id
        if not self.job_store:
            return None
        for job in self.job_store.list_recent(20):
            if job.get("client_id") != client_id:
                continue
            if job.get("status") in {"queued", "running"}:
                return str(job["prompt_id"])
        return None

    def _on_tracker_progress(self, prompt_id: str, state: ProgressState) -> None:
        snap = _state_to_dict(state, status="running")
        with self._lock:
            self._latest[prompt_id] = snap

    def _stop_tracker(self, prompt_id: str) -> None:
        with self._lock:
            tracker = self._trackers.pop(prompt_id, None)
        if tracker is not None:
            try:
                tracker.stop()
            except Exception as exc:
                logger.warning("stop progress tracker failed prompt_id=%s: %s", prompt_id, exc)

    def start(
        self,
        *,
        prompt_id: str,
        client_id: str,
        prompt_snapshot: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> None:
        del prompt_snapshot  # kept for API compatibility
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

        initial = {
            "workflow_progress": 0.0,
            "node_progress": 0.0,
            "current_node_name": "",
            "executed_nodes": 0,
            "total_nodes": len(prompt_snapshot),
            "elapsed_seconds": 0,
            "status": "running",
        }
        with self._lock:
            self._client_prompt[client_id] = prompt_id
            self._latest[prompt_id] = initial

        self._stop_tracker(prompt_id)
        try:
            tracker = ComfyProgressTracker(
                self.comfy_url,
                client_id,
                prompt_id,
                prompt_snapshot,
            )
            tracker.on_progress(lambda state, pid=prompt_id: self._on_tracker_progress(pid, state))
            tracker.start()
            with self._lock:
                self._trackers[prompt_id] = tracker
        except Exception as exc:
            logger.warning("failed to start progress tracker prompt_id=%s: %s", prompt_id, exc)

    def get_progress(self, prompt_id: str) -> dict[str, Any]:
        with self._lock:
            snap = self._latest.get(prompt_id)
            if snap is None:
                return {
                    "success": True,
                    "found": False,
                    "prompt_id": prompt_id,
                    "workflow_progress": 0.0,
                    "node_progress": 0.0,
                    "current_node_name": "",
                    "executed_nodes": 0,
                    "total_nodes": 0,
                    "status": "unknown",
                }
            return {
                "success": True,
                "found": True,
                "prompt_id": prompt_id,
                **snap,
            }

    def log_backend_event(self, client_id: str, message: str | bytes) -> None:
        if isinstance(message, bytes):
            return
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError:
            return
        msg_type = parsed.get("type")
        if not msg_type:
            return
        data = parsed.get("data") or {}
        if not isinstance(data, dict):
            data = {}

        prompt_id = self._resolve_prompt_id(client_id)
        if not prompt_id:
            return

        backend_log = self._run_dir(prompt_id) / "backend.jsonl"
        self._append_jsonl(
            backend_log,
            {
                "ts": _now_iso(),
                "source": "comfy_ws",
                "type": msg_type,
                "data": data,
            },
        )

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
        self._stop_tracker(prompt_id)
        with self._lock:
            to_remove = [cid for cid, pid in self._client_prompt.items() if pid == prompt_id]
            for client_id in to_remove:
                del self._client_prompt[client_id]
            if prompt_id in self._latest:
                self._latest[prompt_id] = {
                    **self._latest[prompt_id],
                    "status": status,
                    "workflow_progress": 100.0
                    if status == "completed"
                    else self._latest[prompt_id].get("workflow_progress", 0),
                    "node_progress": 100.0
                    if status == "completed"
                    else self._latest[prompt_id].get("node_progress", 0),
                }

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
