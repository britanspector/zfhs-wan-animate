"""ComfyUI process lifecycle management."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import httpx


def resolve_python_bin() -> str:
    return os.environ.get("COMFY_PYTHON", sys.executable)


def resolve_conda_lib() -> str:
    python_bin = Path(resolve_python_bin())
    prefix = python_bin.parent.parent
    lib = prefix / "lib"
    return str(lib) if lib.is_dir() else "/usr/lib"


class ComfyManager:
    def __init__(self, *, comfy_url: str, comfy_root: Path, start_script: str, stop_port: int):
        self.comfy_url = comfy_url.rstrip("/")
        self.comfy_root = Path(comfy_root)
        self.start_script = start_script or ""
        self.stop_port = stop_port
        self._starting = False

    def _resolve_ld_library_path(self) -> str:
        cache = Path(os.environ.get("COMFY_LD_CACHE", "/tmp/.comfyui-ld-cache"))
        if cache.is_file():
            return cache.read_text(encoding="utf-8").strip()
        python_bin = resolve_python_bin()
        try:
            out = subprocess.run(
                [
                    python_bin,
                    "-c",
                    (
                        "import site, glob, os; "
                        f"parts=[{resolve_conda_lib()!r}]; "
                        "sp=site.getsitepackages()[0]; "
                        "nv=[p for p in glob.glob(os.path.join(sp,'nvidia','*','lib')) if os.path.isdir(p)]; "
                        "parts.extend(sorted(nv)); "
                        "print(':'.join(parts))"
                    ),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            extra = out.stdout.strip()
            if extra:
                cache.parent.mkdir(parents=True, exist_ok=True)
                cache.write_text(extra, encoding="utf-8")
            return extra
        except Exception:
            return resolve_conda_lib()

    def _comfy_env(self) -> dict[str, str]:
        env = os.environ.copy()
        extra = self._resolve_ld_library_path()
        if extra:
            current = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = f"{extra}:{current}" if current else extra
        return env

    def status(self) -> dict[str, Any]:
        try:
            with httpx.Client(base_url=self.comfy_url, timeout=5.0) as client:
                resp = client.get("/system_stats")
                resp.raise_for_status()
                stats = resp.json()
            return {
                "running": True,
                "starting": self._starting,
                "reason": "ok",
                "version": stats.get("system", {}).get("comfyui_version"),
            }
        except Exception as exc:
            return {
                "running": False,
                "starting": self._starting,
                "reason": str(exc),
            }

    def start(self, *, wait_seconds: float = 120.0) -> dict[str, Any]:
        current = self.status()
        if current["running"]:
            return {"success": True, "already_running": True, **current}

        self._starting = True
        try:
            log_path = self.comfy_root / "wan_animate_comfy_start.log"
            script = Path(self.start_script) if self.start_script else None
            main_py = self.comfy_root / "main.py"
            python_bin = resolve_python_bin()
            if script and script.is_file():
                cmd = ["nohup", "bash", str(script)]
                cwd = str(script.parent)
            elif main_py.is_file():
                cmd = [
                    "nohup",
                    python_bin,
                    str(main_py),
                    "--port",
                    str(self.stop_port),
                    "--listen",
                    "127.0.0.1",
                    "--enable-cors-header",
                    "*",
                ]
                cwd = str(self.comfy_root)
            else:
                raise FileNotFoundError(f"ComfyUI entry not found: {script} or {main_py}")

            with open(log_path, "ab") as logf:
                subprocess.Popen(
                    cmd,
                    cwd=cwd,
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env=self._comfy_env(),
                )

            deadline = time.monotonic() + wait_seconds
            while time.monotonic() < deadline:
                st = self.status()
                if st["running"]:
                    return {"success": True, "already_running": False, **st}
                time.sleep(2)
            return {"success": False, "reason": "timeout waiting for ComfyUI", **self.status()}
        finally:
            self._starting = False

    def stop(self) -> dict[str, Any]:
        pids = subprocess.run(
            ["lsof", "-Pi", f":{self.stop_port}", "-sTCP:LISTEN", "-t"],
            capture_output=True,
            text=True,
            check=False,
        )
        killed: list[str] = []
        for pid in pids.stdout.strip().split():
            if pid:
                subprocess.run(["kill", "-9", pid], check=False)
                killed.append(pid)
        time.sleep(1)
        st = self.status()
        return {"success": not st["running"], "killed_pids": killed, **st}
