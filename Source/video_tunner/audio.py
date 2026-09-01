from __future__ import annotations

import subprocess
from pathlib import Path

from .tools import resolve_tool


def extract_analysis_audio(
    source: str | Path,
    destination: str | Path,
    *,
    sample_rate: int = 16000,
) -> Path:
    """Extract mono 16-bit PCM WAV used by transcription and VAD.

    The source file is only read. The destination is always a separate file.
    """
    source_path = Path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"No existe el vídeo de entrada: {source_path}")

    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            str(destination_path),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo extraer el audio de análisis:\n{completed.stderr}")
    if not destination_path.is_file() or destination_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg terminó sin generar un WAV de análisis válido.")
    return destination_path
