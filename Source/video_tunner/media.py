from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .tools import resolve_tool


def probe_media(source: str | Path) -> dict[str, Any]:
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el vídeo de entrada: {path}")

    ffprobe = resolve_tool("ffprobe")
    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    streams = payload.get("streams", [])
    format_data = payload.get("format", {})

    duration_raw = format_data.get("duration")
    if duration_raw is None:
        raise ValueError("ffprobe no devolvió la duración del archivo.")

    return {
        "file": path.name,
        "duration_seconds": float(duration_raw),
        "video_streams": sum(s.get("codec_type") == "video" for s in streams),
        "audio_streams": sum(s.get("codec_type") == "audio" for s in streams),
        "format_name": format_data.get("format_name"),
    }
