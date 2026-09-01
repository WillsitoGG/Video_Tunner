from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from .tools import resolve_tool


def keep_segments(duration: float, edits: list[dict[str, Any]]) -> list[tuple[float, float]]:
    cuts = sorted(
        (
            max(0.0, float(edit["start"])),
            min(duration, float(edit["end"])),
        )
        for edit in edits
        if edit.get("action") == "remove"
    )

    merged: list[list[float]] = []
    for start, end in cuts:
        if end <= start:
            continue
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)

    segments: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in merged:
        if start > cursor:
            segments.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < duration:
        segments.append((cursor, duration))
    return segments


def render_from_plan(
    source: str | Path,
    plan: dict[str, Any],
    destination: str | Path,
) -> Path:
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()
    if source_path == destination_path:
        raise ValueError("El original nunca puede sobrescribirse.")

    duration = float(plan["source"]["duration_seconds"])
    segments = keep_segments(duration, plan.get("edits", []))
    if not segments:
        raise ValueError("El Edit Plan eliminaría todo el vídeo; render cancelado.")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if len(segments) == 1 and segments[0] == (0.0, duration):
        shutil.copy2(source_path, destination_path)
        return destination_path

    ffmpeg = resolve_tool("ffmpeg")
    filters: list[str] = []
    concat_inputs: list[str] = []
    for index, (start, end) in enumerate(segments):
        filters.append(
            f"[0:v:0]trim=start={start:.6f}:end={end:.6f},setpts=PTS-STARTPTS[v{index}]"
        )
        filters.append(
            f"[0:a:0]atrim=start={start:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a{index}]"
        )
        concat_inputs.append(f"[v{index}][a{index}]")

    filter_complex = ";".join(filters) + ";" + "".join(concat_inputs) + (
        f"concat=n={len(segments)}:v=1:a=1[outv][outa]"
    )

    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-y",
            "-i",
            str(source_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[outv]",
            "-map",
            "[outa]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(destination_path),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo renderizar el Edit Plan:\n{completed.stderr}")
    return destination_path
