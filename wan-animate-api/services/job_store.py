"""Local job history store."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        if not self.path.exists():
            self._write({"jobs": []})

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"jobs": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def create(
        self,
        *,
        prompt_id: str,
        workflow_id: str,
        client_id: str | None = None,
        image: str | None = None,
        video: str | None = None,
        width: int | None = None,
        height: int | None = None,
        seconds: int | None = None,
        input_values: dict | None = None,
        tunables: dict | None = None,
        workflow_variant: str | None = None,
        prompt_snapshot: dict | None = None,
    ) -> dict[str, Any]:
        job = {
            "id": str(uuid4()),
            "prompt_id": prompt_id,
            "workflow_id": workflow_id,
            "workflow_variant": workflow_variant,
            "client_id": client_id,
            "image": image,
            "video": video,
            "width": width,
            "height": height,
            "seconds": seconds,
            "input_values": input_values or {},
            "tunables": tunables or {},
            "prompt_snapshot": prompt_snapshot or {},
            "status": "queued",
            "results": [],
            "error": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        with self._lock:
            data = self._read()
            data["jobs"].insert(0, job)
            data["jobs"] = data["jobs"][:200]
            self._write(data)
        return job

    def update(self, prompt_id: str, **fields) -> dict[str, Any] | None:
        with self._lock:
            data = self._read()
            for job in data["jobs"]:
                if job.get("prompt_id") == prompt_id:
                    job.update(fields)
                    job["updated_at"] = _now()
                    self._write(data)
                    return job
        return None

    def get(self, prompt_id: str) -> dict[str, Any] | None:
        data = self._read()
        for job in data["jobs"]:
            if job.get("prompt_id") == prompt_id:
                return job
        return None

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        data = self._read()
        return data.get("jobs", [])[:limit]
