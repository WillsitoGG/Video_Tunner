from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .tools import resolve_tool

_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
_END_RE = re.compile(r"silence_end:\s*([0-9.]+)\s*\|\s*silence_duration:\s*([0-9.]+)")


@dataclass(frozen=True)
class SilenceInterval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def parse_silencedetect(stderr: str, media_duration: float | None = None) -> list[SilenceInterval]:
    intervals: list[SilenceInterval] = []
    current_start: float | None = None

    for line in stderr.splitlines():
        start_match = _START_RE.search(line)
        if start_match:
            current_start = float(start_match.group(1))
            continue

        end_match = _END_RE.search(line)
        if end_match:
            end = float(end_match.group(1))
            duration = float(end_match.group(2))
            start = current_start if current_start is not None else max(0.0, end - duration)
            if end > start:
                intervals.append(SilenceInterval(start=start, end=end))
            current_start = None

    if current_start is not None and media_duration is not None and media_duration > current_start:
        intervals.append(SilenceInterval(start=current_start, end=media_duration))

    return intervals


def detect_silences(
    source: str | Path,
    *,
    media_duration: float,
    noise_db: float = -40.0,
    min_duration: float = 0.65,
) -> list[SilenceInterval]:
    path = Path(source)
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-af",
            f"silencedetect=noise={noise_db}dB:d={min_duration}",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo analizar silencios:\n{completed.stderr}")
    return parse_silencedetect(completed.stderr, media_duration=media_duration)


def silence_removals(
    intervals: list[SilenceInterval],
    *,
    keep_pause: float,
) -> list[dict[str, float | str]]:
    cuts: list[dict[str, float | str]] = []
    half_keep = max(0.0, keep_pause) / 2.0

    for interval in intervals:
        if interval.duration <= keep_pause:
            continue
        start = interval.start + half_keep
        end = interval.end - half_keep
        if end <= start:
            continue
        cuts.append(
            {
                "action": "remove",
                "kind": "silence",
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(end - start, 6),
                "reason": "Silencio detectado por FFmpeg silencedetect",
                "confidence": 1.0,
            }
        )

    return cuts
