"""ffprobe helpers for reference media inspection."""

from __future__ import annotations

import subprocess
from pathlib import Path


def probe_video_duration(path: Path) -> float:
    """Return video duration in seconds (float). Raises on missing file or ffprobe failure."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Video not found: {path}")
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    try:
        duration = float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Could not parse ffprobe duration for {path}") from exc
    if duration <= 0:
        raise RuntimeError(f"Invalid video duration for {path}: {duration}")
    return duration
