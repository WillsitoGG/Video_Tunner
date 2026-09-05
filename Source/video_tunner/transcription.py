from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from .tools import model_root, portable_strict_mode, runtime_layout


WHISPER_SAMPLE_RATE = 16000
CHUNKED_TRANSCRIPTION_WINDOW_SECONDS = 12.0
CHUNKED_TRANSCRIPTION_HOP_SECONDS = 6.0
CHUNKED_TRANSCRIPTION_STRATEGY = "deterministic_overlap_12s_6s_v1"


class TranscriptionDependencyError(RuntimeError):
    pass


class WhisperModelNotFoundError(RuntimeError):
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
class TranscriptionChunkWindow:
    index: int
    start: float
    end: float
    ownership_start: float
    ownership_end: float


@dataclass(frozen=True)
class TranscriptResult:
    language: str | None
    language_probability: float | None
    model: str
    device: str
    compute_type: str
    segments: tuple[TranscriptSegment, ...]
    strategy: str = "single_pass"
    chunk_window_seconds: float | None = None
    chunk_hop_seconds: float | None = None
    chunk_count: int | None = None

    @property
    def word_count(self) -> int:
        return sum(len(segment.words) for segment in self.segments)


def _model_directory_name(model_name: str) -> str:
    value = model_name.strip()
    if not value:
        raise ValueError("El nombre del modelo Whisper no puede estar vacío.")
    return value.replace("\\", "__").replace("/", "__").replace(":", "_")


def local_whisper_model_path(model_name: str) -> Path:
    return model_root() / "whisper" / _model_directory_name(model_name)


def whisper_model_status(model_name: str) -> dict[str, Any]:
    path = local_whisper_model_path(model_name)
    required = {
        "config.json": (path / "config.json").is_file(),
        "model.bin": (path / "model.bin").is_file(),
        "tokenizer.json": (path / "tokenizer.json").is_file(),
    }
    return {
        "model": model_name,
        "path": str(path),
        "available": path.is_dir() and all(required.values()),
        "required_files": required,
    }


def download_whisper_model(model_name: str, *, replace: bool = False) -> Path:
    """Download a faster-whisper model into the portable Models tree."""
    try:
        from faster_whisper.utils import download_model
    except ImportError as exc:
        raise TranscriptionDependencyError(
            "Falta faster-whisper. El perfil portable de análisis debe incluir "
            "las dependencias ML antes de descargar modelos."
        ) from exc

    destination = local_whisper_model_path(model_name)
    if whisper_model_status(model_name)["available"] and not replace:
        return destination

    layout = runtime_layout()
    cache_dir = layout["cache"] / "huggingface"
    staging_root = layout["temp"] / "model-downloads"
    staging = staging_root / f"{_model_directory_name(model_name)}.partial"

    cache_dir.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    try:
        download_model(
            model_name,
            output_dir=str(staging),
            cache_dir=str(cache_dir),
        )
        required = ("config.json", "model.bin", "tokenizer.json")
        missing = [name for name in required if not (staging / name).is_file()]
        if missing:
            raise RuntimeError(
                "La descarga del modelo Whisper está incompleta; faltan: "
                + ", ".join(missing)
            )

        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if not replace:
                raise RuntimeError(
                    f"Ya existe un modelo incompleto en {destination}. "
                    "Usa --replace para sustituirlo."
                )
            shutil.rmtree(destination)
        shutil.move(str(staging), str(destination))
        return destination
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def _resolve_device_and_compute(device: str, compute_type: str) -> tuple[str, str]:
    if device not in {"auto", "cpu", "cuda"}:
        raise ValueError(f"Dispositivo Whisper no válido: {device}")
    if compute_type != "auto":
        return device if device != "auto" else "cpu", compute_type
    if device == "cuda":
        return "cuda", "float16"
    return "cpu", "int8"


def _resolve_whisper_model_source(model_name: str) -> tuple[str, bool]:
    local_model = local_whisper_model_path(model_name)
    local_status = whisper_model_status(model_name)
    if local_status["available"]:
        return str(local_model), True
    if portable_strict_mode():
        raise WhisperModelNotFoundError(
            f"El modelo Whisper '{model_name}' no está disponible en {local_model}. "
            f"Descárgalo primero con `video-tunner model fetch {model_name}`."
        )
    return model_name, False


def _load_whisper_model(
    model_name: str,
    *,
    device: str,
    compute_type: str,
) -> tuple[Any, str, str]:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionDependencyError(
            "Falta faster-whisper. Instala las dependencias de análisis con "
            "`python -m pip install -e .[analysis]`."
        ) from exc

    resolved_device, resolved_compute = _resolve_device_and_compute(device, compute_type)
    model_source, local_files_only = _resolve_whisper_model_source(model_name)
    download_root = model_root() / "whisper"
    download_root.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        model_source,
        device=resolved_device,
        compute_type=resolved_compute,
        download_root=str(download_root),
        local_files_only=local_files_only,
    )
    return model, resolved_device, resolved_compute


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


def build_transcription_chunk_windows(
    duration_seconds: float,
    *,
    window_seconds: float = CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    hop_seconds: float = CHUNKED_TRANSCRIPTION_HOP_SECONDS,
) -> tuple[TranscriptionChunkWindow, ...]:
    """Build a deterministic fixed grid with one non-overlapping ownership region per chunk.

    For the 12s/6s profile, adjacent chunks overlap by 6s. Their ownership
    boundary is the midpoint of that overlap, so interior chunks own their
    central 6 seconds and every timeline instant belongs to exactly one chunk.
    The first/last chunks additionally own the media edges.
    """
    duration = float(duration_seconds)
    window = float(window_seconds)
    hop = float(hop_seconds)
    if duration < 0.0:
        raise ValueError("La duración de audio no puede ser negativa.")
    if window <= 0.0 or hop <= 0.0 or hop > window:
        raise ValueError("Geometría de chunking inválida.")
    if duration == 0.0:
        return ()

    starts: list[float] = []
    start = 0.0
    while start < duration - 1e-9:
        starts.append(round(start, 9))
        start += hop

    overlap = window - hop
    ownership_margin = overlap / 2.0
    windows: list[TranscriptionChunkWindow] = []
    for index, start in enumerate(starts):
        end = min(duration, start + window)
        ownership_start = 0.0 if index == 0 else min(duration, start + ownership_margin)
        if index == len(starts) - 1:
            ownership_end = duration
        else:
            ownership_end = min(duration, start + window - ownership_margin)
        if ownership_end <= ownership_start + 1e-9:
            continue
        windows.append(
            TranscriptionChunkWindow(
                index=index,
                start=round(start, 9),
                end=round(end, 9),
                ownership_start=round(ownership_start, 9),
                ownership_end=round(ownership_end, 9),
            )
        )
    return tuple(windows)


def _word_midpoint(word: WordTiming, *, offset: float = 0.0) -> float:
    return offset + (float(word.start) + float(word.end)) / 2.0


def merge_chunked_transcript_segments(
    chunks: Iterable[tuple[TranscriptionChunkWindow, tuple[TranscriptSegment, ...]]],
) -> tuple[TranscriptSegment, ...]:
    """Map local chunk timestamps to the master timeline using deterministic ownership.

    No fuzzy text reconciliation occurs. A word is retained iff its global
    midpoint belongs to that chunk's ownership region. Because ownership regions
    tile the timeline without overlap, the same temporal word hypothesis cannot
    be emitted twice merely because the ASR windows overlap.
    """
    merged: list[TranscriptSegment] = []
    ordered = sorted(chunks, key=lambda item: (item[0].start, item[0].index))
    last_window_index = ordered[-1][0].index if ordered else -1

    for window, segments in ordered:
        for segment in segments:
            selected: list[WordTiming] = []
            for word in segment.words:
                midpoint = _word_midpoint(word, offset=window.start)
                in_left = midpoint >= window.ownership_start - 1e-9
                if window.index == last_window_index:
                    in_right = midpoint <= window.ownership_end + 1e-9
                else:
                    in_right = midpoint < window.ownership_end - 1e-9
                if not (in_left and in_right):
                    continue
                selected.append(
                    WordTiming(
                        text=word.text,
                        start=round(window.start + float(word.start), 6),
                        end=round(window.start + float(word.end), 6),
                        probability=word.probability,
                    )
                )
            if not selected:
                continue
            selected.sort(key=lambda item: (item.start, item.end, item.text))
            merged.append(
                TranscriptSegment(
                    text=" ".join(word.text for word in selected).strip(),
                    start=selected[0].start,
                    end=selected[-1].end,
                    words=tuple(selected),
                )
            )

    merged.sort(key=lambda item: (item.start, item.end, item.text))
    return tuple(merged)


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

    model, resolved_device, resolved_compute = _load_whisper_model(
        model_name,
        device=device,
        compute_type=compute_type,
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


def transcribe_audio_chunked(
    audio_wav: str | Path,
    *,
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
    window_seconds: float = CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    hop_seconds: float = CHUNKED_TRANSCRIPTION_HOP_SECONDS,
) -> TranscriptResult:
    """Transcribe deterministic overlapping windows and merge them on the master timeline.

    This is opt-in during Phase 2E hardening. It does not alter `transcribe_audio`
    or the default analysis pipeline. Audio is decoded once through faster-whisper's
    bundled PyAV path, then sliced in-memory. Every chunk is independently decoded
    by Whisper; overlap is reconciled only by deterministic temporal ownership.
    """
    wav_path = Path(audio_wav)
    if not wav_path.is_file():
        raise FileNotFoundError(f"No existe el WAV de análisis: {wav_path}")

    try:
        from faster_whisper.audio import decode_audio
    except ImportError as exc:
        raise TranscriptionDependencyError(
            "Falta faster-whisper/PyAV para decodificar el audio chunked."
        ) from exc

    model, resolved_device, resolved_compute = _load_whisper_model(
        model_name,
        device=device,
        compute_type=compute_type,
    )
    audio = decode_audio(str(wav_path), sampling_rate=WHISPER_SAMPLE_RATE)
    duration = float(len(audio)) / float(WHISPER_SAMPLE_RATE)
    windows = build_transcription_chunk_windows(
        duration,
        window_seconds=window_seconds,
        hop_seconds=hop_seconds,
    )
    if not windows:
        return TranscriptResult(
            language=language,
            language_probability=None,
            model=model_name,
            device=resolved_device,
            compute_type=resolved_compute,
            segments=(),
            strategy=CHUNKED_TRANSCRIPTION_STRATEGY,
            chunk_window_seconds=float(window_seconds),
            chunk_hop_seconds=float(hop_seconds),
            chunk_count=0,
        )

    chunk_results: list[tuple[TranscriptionChunkWindow, tuple[TranscriptSegment, ...]]] = []
    detected_language = language
    detected_probability: float | None = None
    for window in windows:
        start_sample = int(round(window.start * WHISPER_SAMPLE_RATE))
        end_sample = int(round(window.end * WHISPER_SAMPLE_RATE))
        chunk_audio = audio[start_sample:end_sample]
        raw_segments, info = model.transcribe(
            chunk_audio,
            language=detected_language,
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=True,
        )
        segments = _normalise_segments(raw_segments)
        if detected_language is None:
            detected_language = getattr(info, "language", None)
            probability = getattr(info, "language_probability", None)
            detected_probability = None if probability is None else float(probability)
        elif detected_probability is None and language is None:
            probability = getattr(info, "language_probability", None)
            detected_probability = None if probability is None else float(probability)
        chunk_results.append((window, segments))

    merged = merge_chunked_transcript_segments(chunk_results)
    return TranscriptResult(
        language=detected_language,
        language_probability=detected_probability,
        model=model_name,
        device=resolved_device,
        compute_type=resolved_compute,
        segments=merged,
        strategy=CHUNKED_TRANSCRIPTION_STRATEGY,
        chunk_window_seconds=float(window_seconds),
        chunk_hop_seconds=float(hop_seconds),
        chunk_count=len(windows),
    )


def transcript_to_dict(result: TranscriptResult) -> dict[str, Any]:
    return {
        "schema_version": 2,
        "engine": "faster-whisper",
        "model": result.model,
        "device": result.device,
        "compute_type": result.compute_type,
        "language": result.language,
        "language_probability": result.language_probability,
        "strategy": {
            "name": result.strategy,
            "chunk_window_seconds": result.chunk_window_seconds,
            "chunk_hop_seconds": result.chunk_hop_seconds,
            "chunk_count": result.chunk_count,
        },
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
    minutes, remainder = divmod(milliseconds % 3_600_000, 60_000)
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
