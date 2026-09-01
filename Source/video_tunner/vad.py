from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


class VadDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class SpeechInterval:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def _merge_speech(intervals: list[SpeechInterval], duration: float) -> list[SpeechInterval]:
    normalised = sorted(
        (
            SpeechInterval(max(0.0, item.start), min(duration, item.end))
            for item in intervals
            if item.end > item.start
        ),
        key=lambda item: item.start,
    )
    merged: list[SpeechInterval] = []
    for item in normalised:
        if not merged or item.start > merged[-1].end:
            merged.append(item)
        else:
            previous = merged[-1]
            merged[-1] = SpeechInterval(previous.start, max(previous.end, item.end))
    return merged


def detect_speech(
    audio_wav: str | Path,
    *,
    threshold: float = 0.5,
    min_silence_ms: int = 250,
    speech_pad_ms: int = 100,
) -> list[SpeechInterval]:
    """Detect speech with the packaged silero-vad Python library.

    No network call is performed by Video_Tunner. The dependency/model packaging
    will be validated separately for the final Windows portable build.
    """
    wav_path = Path(audio_wav)
    if not wav_path.is_file():
        raise FileNotFoundError(f"No existe el WAV de análisis: {wav_path}")
    try:
        from silero_vad import get_speech_timestamps, load_silero_vad, read_audio
    except ImportError as exc:
        raise VadDependencyError(
            "Falta silero-vad. Instala las dependencias de análisis con "
            "`python -m pip install -e .[analysis]`."
        ) from exc

    model = load_silero_vad()
    audio = read_audio(str(wav_path), sampling_rate=16000)
    timestamps: list[dict[str, Any]] = get_speech_timestamps(
        audio,
        model,
        sampling_rate=16000,
        threshold=threshold,
        min_silence_duration_ms=min_silence_ms,
        speech_pad_ms=speech_pad_ms,
        return_seconds=True,
    )
    return [
        SpeechInterval(start=float(item["start"]), end=float(item["end"]))
        for item in timestamps
        if float(item["end"]) > float(item["start"])
    ]


def non_speech_gaps(
    speech_intervals: list[SpeechInterval],
    *,
    duration: float,
    min_duration: float = 0.0,
) -> list[tuple[float, float]]:
    """Return the complement of speech intervals inside [0, duration]."""
    if duration < 0:
        raise ValueError("La duración no puede ser negativa.")
    merged = _merge_speech(speech_intervals, duration)
    gaps: list[tuple[float, float]] = []
    cursor = 0.0
    for item in merged:
        if item.start - cursor >= min_duration and item.start > cursor:
            gaps.append((cursor, item.start))
        cursor = max(cursor, item.end)
    if duration - cursor >= min_duration and duration > cursor:
        gaps.append((cursor, duration))
    return gaps
