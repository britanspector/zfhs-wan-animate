"""ComfyUI HTTP client for zfhs-wan-animate."""

from __future__ import annotations

import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


@dataclass
class OutputFile:
    filename: str
    subfolder: str = ""
    file_type: str = "output"
    format: str | None = None

    @property
    def view_url(self) -> str:
        raise NotImplementedError

    def local_path(self, comfy_root: Path) -> Path:
        base = comfy_root / "output"
        if self.subfolder:
            return base / self.subfolder / self.filename
        return base / self.filename

    def output_url(self, api_base: str = "") -> str:
        segs: list[str] = []
        if self.subfolder:
            segs.extend(quote(part, safe="") for part in self.subfolder.split("/") if part)
        segs.append(quote(self.filename, safe=""))
        path = "/output/" + "/".join(segs)
        if api_base:
            return f"{api_base.rstrip('/')}{path}"
        return path


@dataclass
class ComfyOutput(OutputFile):
    base_url: str = ""

    @property
    def view_url(self) -> str:
        return build_view_url(
            self.base_url,
            filename=self.filename,
            file_type=self.file_type,
            subfolder=self.subfolder,
        )


def build_view_url(
    base_url: str,
    *,
    filename: str,
    file_type: str = "output",
    subfolder: str = "",
) -> str:
    params = f"filename={quote(filename)}&type={quote(file_type)}"
    if subfolder:
        params += f"&subfolder={quote(subfolder)}"
    path = f"/view?{params}"
    if base_url:
        return f"{base_url.rstrip('/')}{path}"
    return path


class ComfyClient:
    def __init__(self, base_url: str, *, comfy_root: Path | None = None, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.comfy_root = comfy_root or Path("/root/ComfyUI")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ComfyClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def check_ready(self) -> dict[str, Any]:
        resp = self._client.get("/system_stats")
        resp.raise_for_status()
        return resp.json()

    def upload_image(self, path: Path, *, subfolder: str = "", overwrite: bool = True) -> str:
        return self._upload(path, endpoint="/upload/image", field="image", subfolder=subfolder, overwrite=overwrite)

    def upload_video(self, path: Path, *, subfolder: str = "", overwrite: bool = True) -> str:
        try:
            return self._upload(path, endpoint="/upload/image", field="image", subfolder=subfolder, overwrite=overwrite)
        except httpx.HTTPError:
            return self._copy_to_input(path)

    def upload_file_bytes(
        self,
        filename: str,
        content: bytes,
        *,
        subfolder: str = "",
        overwrite: bool = True,
    ) -> dict[str, str]:
        data: dict[str, str] = {"overwrite": "true" if overwrite else "false"}
        if subfolder:
            data["subfolder"] = subfolder
        files = {"image": (filename, content, _mime_type(Path(filename)))}
        resp = self._client.post("/upload/image", data=data, files=files)
        resp.raise_for_status()
        body = resp.json()
        return {
            "name": body.get("name") or filename,
            "subfolder": body.get("subfolder") or subfolder or "",
            "type": body.get("type") or "input",
        }

    def _upload(
        self,
        path: Path,
        *,
        endpoint: str,
        field: str,
        subfolder: str,
        overwrite: bool,
    ) -> str:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(path)

        data: dict[str, str] = {"overwrite": "true" if overwrite else "false"}
        if subfolder:
            data["subfolder"] = subfolder

        with path.open("rb") as f:
            files = {field: (path.name, f, _mime_type(path))}
            resp = self._client.post(endpoint, data=data, files=files)
        resp.raise_for_status()
        body = resp.json()
        name = body.get("name") or path.name
        if subfolder and body.get("subfolder"):
            return f"{body['subfolder']}/{name}"
        return name

    def _copy_to_input(self, path: Path) -> str:
        dest_dir = self.comfy_root / "input"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / path.name
        shutil.copy2(path, dest)
        return path.name

    def queue_prompt(self, prompt: dict[str, Any], *, client_id: str | None = None) -> str:
        cid = client_id or str(uuid.uuid4())
        resp = self._client.post("/prompt", json={"prompt": prompt, "client_id": cid})
        resp.raise_for_status()
        body = resp.json()
        prompt_id = body.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI /prompt missing prompt_id: {body}")
        return prompt_id

    def get_queue(self) -> dict[str, Any]:
        resp = self._client.get("/queue")
        resp.raise_for_status()
        return resp.json()

    def interrupt(self) -> None:
        resp = self._client.post("/interrupt")
        resp.raise_for_status()

    def get_history(self, prompt_id: str | None = None) -> dict[str, Any]:
        if prompt_id:
            resp = self._client.get(f"/history/{prompt_id}")
        else:
            resp = self._client.get("/history")
        resp.raise_for_status()
        return resp.json()

    def get_history_entry(self, prompt_id: str) -> dict[str, Any] | None:
        data = self.get_history(prompt_id)
        if not data:
            return None
        return data.get(prompt_id) or data

    def wait_for_completion(
        self,
        prompt_id: str,
        *,
        poll_interval: float = 2.0,
        timeout: float = 1200.0,
    ) -> dict[str, Any]:
        import time

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            history = self.get_history_entry(prompt_id)
            if history and history.get("outputs"):
                status = history.get("status", {})
                if status.get("status_str") == "error":
                    messages = status.get("messages", [])
                    raise RuntimeError(f"ComfyUI prompt failed: {messages}")
                return history
            if history and history.get("status", {}).get("completed"):
                return history
            time.sleep(poll_interval)
        raise TimeoutError(f"Timed out waiting for prompt {prompt_id} after {timeout}s")

    def resolve_outputs(self, history: dict[str, Any], node_id: str = "867") -> list[ComfyOutput]:
        outputs = history.get("outputs", {})
        node_out = outputs.get(str(node_id), {})
        files: list[ComfyOutput] = []

        for key in ("gifs", "videos", "images"):
            for item in node_out.get(key, []) or []:
                if not isinstance(item, dict):
                    continue
                filename = item.get("filename")
                if not filename:
                    continue
                files.append(
                    ComfyOutput(
                        filename=filename,
                        subfolder=item.get("subfolder", "") or "",
                        file_type=item.get("type", "output"),
                        format=item.get("format"),
                        base_url=self.base_url,
                    )
                )
        return files

    def fetch_view(self, *, filename: str, file_type: str = "input", subfolder: str = "") -> httpx.Response:
        params: dict[str, str] = {"filename": filename, "type": file_type}
        if subfolder:
            params["subfolder"] = subfolder
        resp = self._client.get("/view", params=params)
        resp.raise_for_status()
        return resp


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        return "image/png" if suffix == ".png" else f"image/{suffix.lstrip('.')}"
    if suffix in {".mp4", ".webm", ".mov", ".avi", ".mkv"}:
        return "video/mp4" if suffix == ".mp4" else f"video/{suffix.lstrip('.')}"
    return "application/octet-stream"
