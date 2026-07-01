"""ComfyUI WebSocket progress tracking for Notebook / CLI."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable
from urllib.parse import urlparse, urlunparse

from zfhs_wan_animate.runner import PollResult


@dataclass
class ProgressState:
    workflow_progress: float = 0.0
    node_progress: float = 0.0
    current_node_name: str = ""
    executed_nodes: int = 0
    total_nodes: int = 0
    elapsed_seconds: int = 0


def _comfy_ws_url(comfy_url: str, client_id: str) -> str:
    parsed = urlparse(comfy_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    netloc = parsed.netloc or parsed.path
    return urlunparse((scheme, netloc, "/ws", "", f"clientId={client_id}", ""))


def _update_overall(executed_count: int, node_pct: float, total_nodes: int) -> float:
    if total_nodes <= 0:
        return 0.0
    current_fraction = min(1.0, node_pct / 100.0) if node_pct > 0 else 0.0
    completed = max(0, executed_count - 1)
    return min(100.0, ((completed + current_fraction) / total_nodes) * 100.0)


class ComfyProgressTracker:
    """Subscribe to ComfyUI /ws progress for a single prompt."""

    def __init__(
        self,
        comfy_url: str,
        client_id: str,
        prompt_id: str,
        prompt_snapshot: dict[str, Any],
    ) -> None:
        self.comfy_url = comfy_url
        self.client_id = client_id
        self.prompt_id = prompt_id
        self.prompt_snapshot = prompt_snapshot
        self.total_nodes = len(prompt_snapshot)
        self.state = ProgressState(total_nodes=self.total_nodes)
        self._executed: set[str] = set()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._start = time.monotonic()
        self._callbacks: list[Callable[[ProgressState], None]] = []

    def on_progress(self, callback: Callable[[ProgressState], None]) -> None:
        self._callbacks.append(callback)

    def _notify(self) -> None:
        with self._lock:
            snapshot = ProgressState(**vars(self.state))
        for cb in self._callbacks:
            cb(snapshot)

    def _set_state(self, **kwargs: Any) -> None:
        with self._lock:
            for key, value in kwargs.items():
                setattr(self.state, key, value)
            self.state.elapsed_seconds = int(time.monotonic() - self._start)
        self._notify()

    def _handle_message(self, raw: str) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return
        msg_type = msg.get("type")
        data = msg.get("data") or {}
        if msg_type == "execution_start":
            self._executed.clear()
            return
        if msg_type == "progress":
            value = float(data.get("value") or 0)
            max_val = float(data.get("max") or 1)
            node_pct = min(100.0, (value / max_val) * 100.0) if max_val > 0 else 0.0
            self._set_state(
                node_progress=node_pct,
                workflow_progress=_update_overall(len(self._executed), node_pct, self.total_nodes),
            )
            return
        if msg_type != "executing":
            return
        pid = data.get("prompt_id")
        if pid and pid != self.prompt_id:
            return
        node = data.get("node")
        if node:
            self._executed.add(str(node))
            node_def = self.prompt_snapshot.get(str(node), {})
            meta = node_def.get("_meta") or {}
            title = meta.get("title") or node_def.get("class_type") or str(node)
            with self._lock:
                node_pct = self.state.node_progress
            self._set_state(
                current_node_name=f"{node} · {title}",
                executed_nodes=len(self._executed),
                total_nodes=self.total_nodes,
                node_progress=0.0,
                workflow_progress=_update_overall(len(self._executed), node_pct, self.total_nodes),
            )
        elif pid == self.prompt_id:
            self._set_state(workflow_progress=100.0, node_progress=100.0)

    def _run(self) -> None:
        try:
            import websockets
        except ImportError as exc:
            raise RuntimeError("websockets package required for progress tracking") from exc

        ws_url = _comfy_ws_url(self.comfy_url, self.client_id)

        async def _listen() -> None:
            async with websockets.connect(ws_url, open_timeout=10) as ws:
                while not self._stop.is_set():
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="ignore")
                    self._handle_message(raw)

        import asyncio

        asyncio.run(_listen())

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="comfy-progress", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self._thread = None


def wait_for_prompt(
    *,
    comfy_url: str,
    client_id: str,
    prompt_id: str,
    prompt_snapshot: dict[str, Any],
    poll_fn: Callable[..., PollResult],
    poll_kwargs: dict[str, Any],
    timeout_sec: float,
    poll_interval: float = 3.0,
    on_progress: Callable[[ProgressState], None] | None = None,
) -> PollResult:
    """Poll prompt completion while streaming ComfyUI WebSocket progress."""
    tracker = ComfyProgressTracker(comfy_url, client_id, prompt_id, prompt_snapshot)
    if on_progress:
        tracker.on_progress(on_progress)
    tracker.start()

    start = time.monotonic()
    polled: PollResult | None = None
    try:
        while time.monotonic() - start < timeout_sec:
            polled = poll_fn(prompt_id, **poll_kwargs)
            if not polled.pending:
                break
            tracker._set_state(elapsed_seconds=int(time.monotonic() - start))
            time.sleep(poll_interval)
    finally:
        tracker.stop()

    if polled is None or polled.pending:
        raise TimeoutError(
            f"轮询超时（{int(timeout_sec)}s）。任务可能仍在 ComfyUI 队列中，prompt_id={prompt_id}"
        )
    return polled
