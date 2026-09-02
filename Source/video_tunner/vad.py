from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    """Detect speech using faster-whisper's bundled Silero VAD ONNX model.

    This deliberately avoids the standalone ``silero-vad`` Python package,
    whose default installation brings Torch and torchaudio. faster-whisper
    already depends on ONNX Runtime and ships the Silero VAD ONNX asset needed
    for its own VAD implementation, so reusing that backend keeps the portable
    dependency graph smaller.
    """
    wav_path = Path(audio_wav)
    if not wav_path.is_file():
        raise FileNotFoundError(f"No existe el WAV de análisis: {wav_path}")

    try:
        from faster_whisper.audio import decode_audio
        from faster_whisper.vad import VadOptions, get_speech_timestamps
    except ImportError as exc:
        raise VadDependencyError(
            "Falta faster-whisper/ONNX Runtime. Instala las dependencias de análisis con "
            "`python -m pip install -e .[analysis]`."
        ) from exc

    audio = decode_audio(str(wav_path), sampling_rate=16000)
    options = VadOptions(
        threshold=threshold,
        min_speech_duration_ms=0,
        min_silence_duration_ms=min_silence_ms,
        speech_pad_ms=speech_pad_ms,
    )
    timestamps = get_speech_timestamps(audio, vad_options=options, sampling_rate=16000)
    return [
        SpeechInterval(start=float(item["start"]) / 16000.0, end=float(item["end"]) / 16000.0)
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
