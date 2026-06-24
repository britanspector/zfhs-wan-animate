#!/usr/bin/env python3
"""Quick test for audio mux fallback (no ComfyUI)."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from zfhs_wan_animate.audio_mux import ffmpeg_available, has_audio_stream, mux_reference_audio  # noqa: E402


def main() -> int:
    if not ffmpeg_available():
        print("SKIP: ffmpeg/ffprobe not available")
        return 0

    cfg_path = ROOT / "config" / "default.yaml"
    import yaml

    with cfg_path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    ref = Path(cfg["samples"]["video"])
    if not ref.is_file():
        print(f"SKIP: sample video missing: {ref}")
        return 0

    assert has_audio_stream(ref), "sample reference video should have audio"
    print(f"OK sample has audio: {ref}")

    # Create silent video clip for mux test
    with tempfile.TemporaryDirectory() as tmp:
        silent = Path(tmp) / "silent.mp4"
        import subprocess

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:d=1",
                "-c:v",
                "libx264",
                "-t",
                "1",
                str(silent),
            ],
            capture_output=True,
            check=True,
        )
        assert not has_audio_stream(silent), "test clip should be silent"
        out = mux_reference_audio(silent, ref)
        assert has_audio_stream(out), "muxed output should have audio"
        print(f"OK mux_reference_audio -> {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
