"""Resolve public-facing URLs for gateway / AutoDL deployments."""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote, urlparse


def _is_local_base(base: str) -> bool:
    if not base:
        return True
    lowered = base.lower()
    return "127.0.0.1" in lowered or "localhost" in lowered


def resolve_public_base_url(settings: dict[str, Any], request: Any | None = None) -> str:
    """Return external base URL (no trailing slash), or '' for same-origin relative paths."""
    for key in ("WAN_ANIMATE_PUBLIC_BASE_URL", "AutoDLService6008URL"):
        val = os.environ.get(key, "").strip()
        if val:
            return val.rstrip("/")

    cfg_public = settings.get("public_base_url") or settings.get("api", {}).get("public_base_url", "")
    if cfg_public and not _is_local_base(str(cfg_public)):
        return str(cfg_public).rstrip("/")

    if request is not None:
        forwarded_host = request.headers.get("x-forwarded-host")
        forwarded_proto = request.headers.get("x-forwarded-proto", "http")
        if forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
        base = str(request.base_url).rstrip("/")
        if _is_local_base(base):
            return ""
        return base

    return ""


def build_output_path_url(base: str, subfolder: str, filename: str) -> str:
    """Build /output/... URL; base empty => relative path for same-origin gateway."""
    segs: list[str] = []
    if subfolder:
        segs.extend(quote(part, safe="") for part in subfolder.split("/") if part)
    segs.append(quote(filename, safe=""))
    path = "/output/" + "/".join(segs)
    if base:
        return f"{base.rstrip('/')}{path}"
    return path


def build_api_view_path_url(base: str, filename: str, file_type: str = "input", subfolder: str = "") -> str:
    """Build /api/comfy/view?... URL for sample previews."""
    params = f"filename={quote(filename)}&type={quote(file_type)}"
    if subfolder:
        params += f"&subfolder={quote(subfolder)}"
    path = f"/api/comfy/view?{params}"
    if base:
        return f"{base.rstrip('/')}{path}"
    return path


def normalize_media_url(url: str, public_base: str = "") -> str:
    """Rewrite localhost absolute URLs to relative or public gateway URLs."""
    if not url:
        return url
    if url.startswith("/"):
        return f"{public_base}{url}" if public_base else url
    if url.startswith("http://127.0.0.1") or url.startswith("http://localhost"):
        try:
            parsed = urlparse(url)
            rel = parsed.path + (f"?{parsed.query}" if parsed.query else "")
            return f"{public_base}{rel}" if public_base else rel
        except Exception:
            return url
    return url
