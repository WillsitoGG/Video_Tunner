from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .tools import model_root


class TranscriptionDependencyError(RuntimeError):
    pass


@dataclass(frozen=True)
class WordTiming:
    text: str
    start: float
    end: float
    probability: float | None = None


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: tuple[WordTiming, ...]


@dataclass(frozen=True)
class TranscriptResult:
    language: str | None
    language_probability: float | None
    model: str
    device: str
    compute_type: str
    segments: tuple[TranscriptSegment, ...]

    @property
    def word_count(self) -> int:
        return sum(len(segment.words) for segment in self.segments)


def _resolve_device_and_compute(device: str, compute_type: str) -> tuple[str, str]:
    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"Dispositivo Whisper no válido: {device}")
    if compute_type != "auto":
        return device if device != "auto" else "cpu", compute_type
    if device == "cuda":
        return "cuda", "float16"
    # Conservative portable default. GPU selection will become explicit during packaging.
    return "cpu", "int8"


def _normalise_segments(raw_segments: Iterable[Any]) -> tuple[TranscriptSegment, ...]:
    result: list[TranscriptSegment] = []
    for segment in raw_segments:
        start = float(segment.start)
        end = float(segment.end)
        if end < start:
            continue
        words: list[WordTiming] = []
        for word in (segment.words or []):
            if word.start is None or word.end is None:
                continue
            word_start = float(word.start)
            word_end = float(word.end)
            if word_end < word_start:
                continue
            probability = None if getattr(word, "probability", None) is None else float(word.probability)
            words.append(
                WordTiming(
                    text=str(word.word).strip(),
                    start=word_start,
                    end=word_end,
                    probability=probability,
                )
            )
        result.append(
            TranscriptSegment(
                text=str(segment.text).strip(),
                start=start,
                end=end,
                words=tuple(words),
            )
        )
    return tuple(result)


def transcribe_audio(
    audio_wav: str | Path,
    *,
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
) -> TranscriptResult:
    """Transcribe locally with faster-whisper and word-level timestamps."""
    wav_path = Path(audio_wav)
    if not wav_path.is_file():
        raise FileNotFoundError(f"No existe el WAV de análisis: {wav_path}")

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionDependencyError(
            "Falta faster-whisper. Instala las dependencias de análisis con "
            "`python -m pip install -e .[analysis]`."
        ) from exc

    resolved_device, resolved_compute = _resolve_device_and_compute(device, compute_type)
    download_root = model_root() / "whisper"
    download_root.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        model_name,
        device=resolved_device,
        compute_type=resolved_compute,
        download_root=str(download_root),
    )
    raw_segments, info = model.transcribe(
        str(wav_path),
        language=language,
        word_timestamps=True,
        vad_filter=False,
    )
    segments = _normalise_segments(raw_segments)
    return TranscriptResult(
        language=getattr(info, "language", None),
        language_probability=(
            None
            if getattr(info, "language_probability", None) is None
            else float(info.language_probability)
        ),
        model=model_name,
        device=resolved_device,
        compute_type=resolved_compute,
        segments=segments,
    )


def transcript_to_dict(result: TranscriptResult) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "engine": "faster-whisper",
        "model": result.model,
        "device": result.device,
        "compute_type": result.compute_type,
        "language": result.language,
        "language_probability": result.language_probability,
        "word_count": result.word_count,
        "segments": [
            {
                "text": segment.text,
                "start": round(segment.start, 6),
                "end": round(segment.end, 6),
                "words": [asdict(word) for word in segment.words],
            }
            for segment in result.segments
        ],
    }


def write_transcript_json(result: TranscriptResult, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(transcript_to_dict(result), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def write_transcript_txt(result: TranscriptResult, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = " ".join(segment.text for segment in result.segments if segment.text).strip()
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    return path


def _srt_timestamp(seconds: float) -> str:
    milliseconds = max(0, int(round(seconds * 1000)))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(result: TranscriptResult, destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks: list[str] = []
    index = 1
    for segment in result.segments:
        if not segment.text or segment.end <= segment.start:
            continue
        blocks.append(
            f"{index}\n{_srt_timestamp(segment.start)} --> {_srt_timestamp(segment.end)}\n{segment.text}"
        )
        index += 1
    path.write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
    return path
