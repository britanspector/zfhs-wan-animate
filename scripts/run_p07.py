#!/usr/bin/env python3
"""CLI entry for P07 Wan2.2 Animate generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zfhs_wan_animate.runner import load_config, run_p07  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    cfg = load_config()
    defaults = cfg.get("defaults", {})
    samples = cfg.get("samples", {})

    parser = argparse.ArgumentParser(description="Run P07 Wan2.2 Animate V4 workflow via ComfyUI")
    parser.add_argument("--image", type=Path, default=Path(samples.get("image", "")) if samples.get("image") else None)
    parser.add_argument("--video", type=Path, default=Path(samples.get("video", "")) if samples.get("video") else None)
    parser.add_argument("--width", type=int, default=int(defaults.get("width", 468)))
    parser.add_argument("--height", type=int, default=int(defaults.get("height", 832)))
    parser.add_argument("--seconds", type=int, default=int(defaults.get("seconds", 30)))
    parser.add_argument("--comfy-url", default=None, help="ComfyUI base URL (default: config or COMFYUI_URL)")
    parser.add_argument("--comfy-root", type=Path, default=None, help="ComfyUI install root for output paths")
    parser.add_argument("--workflow", type=Path, default=None, help="Workflow JSON path")
    parser.add_argument("--config", type=Path, default=None, help="Config YAML path")
    args = parser.parse_args(argv)

    if args.config:
        cfg = load_config(args.config)

    if not args.image or not args.video:
        parser.error("--image and --video are required (or set samples in config/default.yaml)")

    print(f"ComfyUI: {args.comfy_url or cfg.get('comfy_url')}")
    print(f"Image:   {args.image}")
    print(f"Video:   {args.video}")
    print(f"Size:    {args.width}x{args.height}, {args.seconds}s")
    print("Submitting workflow...")

    result = run_p07(
        image_path=args.image,
        video_path=args.video,
        width=args.width,
        height=args.height,
        seconds=args.seconds,
        comfy_url=args.comfy_url,
        comfy_root=args.comfy_root,
        workflow_path=args.workflow,
        config=cfg,
    )

    print(f"\nDone in {result.elapsed_seconds:.1f}s")
    print(f"prompt_id: {result.prompt_id}")

    if not result.outputs:
        print("WARNING: No outputs found on node 867", file=sys.stderr)
        return 1

    for i, out in enumerate(result.outputs):
        local = out.local_path(result.comfy_root)
        print(f"output[{i}] local: {local}")
        print(f"output[{i}] url:   {out.view_url}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
