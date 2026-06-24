#!/usr/bin/env python3
"""Verify P07 assets, models, custom nodes, and ComfyUI connectivity."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zfhs_wan_animate.audio_mux import ffmpeg_available, has_audio_stream  # noqa: E402
from zfhs_wan_animate.comfy_client import ComfyClient  # noqa: E402
from zfhs_wan_animate.runner import load_config  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify P07 assets and ComfyUI connectivity")
    parser.add_argument(
        "--strict-models",
        action="store_true",
        help="Treat missing model files as errors (default: warn only)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Only check ComfyUI connectivity and ffmpeg",
    )
    args = parser.parse_args()

    cfg = load_config()
    comfy_root = Path(os.environ.get("COMFYUI_ROOT", cfg.get("comfy_root", "/app/ComfyUI")))
    comfy_url = os.environ.get("COMFYUI_URL", cfg.get("comfy_url", "http://127.0.0.1:6006"))

    errors: list[str] = []
    warnings: list[str] = []
    ok: list[str] = []

    if not args.quick:
        workflow_paths: list[Path] = []
        variants = cfg.get("workflows") or {}
        if variants:
            for key, meta in variants.items():
                rel = meta.get("file", "")
                if rel:
                    p = Path(rel)
                    workflow_paths.append(p if p.is_absolute() else ROOT / p)
        else:
            workflow_paths.append(ROOT / cfg.get("workflow_path", "workflows/p07_animate_v4.json"))

        for workflow in workflow_paths:
            if workflow.is_file():
                ok.append(f"workflow: {workflow}")
            else:
                errors.append(f"workflow missing: {workflow}")

        models_manifest = ROOT / "manifest" / "models.yaml"
        with models_manifest.open(encoding="utf-8") as f:
            models_data = yaml.safe_load(f) or {}

        for item in models_data.get("models", []):
            rel = item.get("path", "")
            category = item.get("category", "")
            full = comfy_root / "models" / category / rel
            if full.is_file():
                ok.append(f"model: {category}/{rel}")
            elif args.strict_models:
                errors.append(f"model missing: {full}")
            else:
                warnings.append(f"model missing (mount required): {full}")

        nodes_manifest = ROOT / "manifest" / "custom_nodes.yaml"
        with nodes_manifest.open(encoding="utf-8") as f:
            nodes_data = yaml.safe_load(f) or {}

        for item in nodes_data.get("required", []):
            name = item.get("name", "")
            full = comfy_root / "custom_nodes" / name
            if full.is_dir():
                ok.append(f"custom_node: {name}")
            else:
                errors.append(f"custom_node missing: {full}")

    try:
        with ComfyClient(comfy_url, comfy_root=comfy_root, timeout=10.0) as client:
            stats = client.check_ready()
        version = stats.get("system", {}).get("comfyui_version", "unknown")
        ok.append(f"ComfyUI reachable at {comfy_url} (version {version})")
    except Exception as exc:
        errors.append(f"ComfyUI unreachable at {comfy_url}: {exc}")

    if ffmpeg_available():
        ok.append("ffmpeg/ffprobe available")
    else:
        errors.append("ffmpeg/ffprobe not available (audio fallback disabled)")

    if not args.quick:
        sample_video = cfg.get("samples", {}).get("video")
        if sample_video and Path(sample_video).is_file():
            if has_audio_stream(Path(sample_video)):
                ok.append(f"sample video has audio: {sample_video}")
            else:
                warnings.append(f"sample video has no audio track: {sample_video}")

    print(f"=== zfhs-wan-animate verify ({len(ok)} ok, {len(warnings)} warn, {len(errors)} errors) ===\n")
    for line in ok:
        print(f"  OK   {line}")
    for line in warnings:
        print(f"  WARN {line}")
        if not args.strict_models:
            print("        See docs/ASSETS_MIGRATION.md for model mount instructions.")
    for line in errors:
        print(f"  FAIL {line}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
