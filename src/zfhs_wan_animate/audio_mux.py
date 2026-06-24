"""ffmpeg fallback: mux reference video audio into output."""

from __future__ import annotations

import subprocess
from pathlib import Path


def has_audio_stream(path: Path) -> bool:
    path = Path(path)
    if not path.is_file():
        return False
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return "audio" in result.stdout


def mux_reference_audio(video_path: Path, ref_video: Path, out_path: Path | None = None) -> Path:
    video_path = Path(video_path)
    ref_video = Path(ref_video)
    if out_path is None:
        out_path = video_path.with_name(f"{video_path.stem}_with_audio{video_path.suffix}")
    else:
        out_path = Path(out_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(ref_video),
        "-c:v",
        "copy",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out_path


def ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        subprocess.run(["ffprobe", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False
