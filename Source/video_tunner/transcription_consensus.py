from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .transcription import (
    CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    WHISPER_SAMPLE_RATE,
    TranscriptResult,
    TranscriptSegment,
    TranscriptionChunkWindow,
    TranscriptionDependencyError,
    WordTiming,
    _load_whisper_model,
    _normalise_segments,
    build_transcription_chunk_windows,
    merge_chunked_transcript_segments,
)


MIN_REPEAT_CONSENSUS_TOKENS = 3
MAX_REPEAT_CONSENSUS_TOKENS = 7
REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS = 0.35


@dataclass(frozen=True)
class RepeatHypothesis:
    window_index: int
    phrase: tuple[str, ...]
    words: tuple[WordTiming, ...]
    first_start: float
    first_end: float
    second_start: float
    second_end: float


def _normalise_token(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", asciiish)


def _global_words(
    window: TranscriptionChunkWindow,
    segments: tuple[TranscriptSegment, ...],
) -> tuple[WordTiming, ...]:
    words = [
        WordTiming(
            text=word.text,
            start=round(window.start + float(word.start), 6),
            end=round(window.start + float(word.end), 6),
            probability=word.probability,
        )
        for segment in segments
        for word in segment.words
    ]
    words.sort(key=lambda item: (item.start, item.end, item.text))
    return tuple(words)


def _repeat_hypotheses(
    window: TranscriptionChunkWindow,
    segments: tuple[TranscriptSegment, ...],
) -> tuple[RepeatHypothesis, ...]:
    words = _global_words(window, segments)
    tokens = tuple(_normalise_token(word.text) for word in words)
    results: list[RepeatHypothesis] = []
    index = 0
    while index < len(words):
        matched: RepeatHypothesis | None = None
        max_size = min(MAX_REPEAT_CONSENSUS_TOKENS, (len(words) - index) // 2)
        for size in range(max_size, MIN_REPEAT_CONSENSUS_TOKENS - 1, -1):
            first = tokens[index : index + size]
            second = tokens[index + size : index + (2 * size)]
            if not first or any(not token for token in first) or first != second:
                continue
            repeated_words = words[index : index + (2 * size)]
            matched = RepeatHypothesis(
                window_index=window.index,
                phrase=first,
                words=repeated_words,
                first_start=repeated_words[0].start,
                first_end=repeated_words[size - 1].end,
                second_start=repeated_words[size].start,
                second_end=repeated_words[-1].end,
            )
            break
        if matched is None:
            index += 1
            continue
        results.append(matched)
        index += len(matched.words)
    return tuple(results)


def _timings_agree(
    left: RepeatHypothesis,
    right: RepeatHypothesis,
    *,
    tolerance_seconds: float,
) -> bool:
    return all(
        abs(a - b) <= tolerance_seconds
        for a, b in (
            (left.first_start, right.first_start),
            (left.first_end, right.first_end),
            (left.second_start, right.second_start),
            (left.second_end, right.second_end),
        )
    )


def _owner_for_time(
    ordered_chunks: list[tuple[TranscriptionChunkWindow, tuple[TranscriptSegment, ...]]],
    timestamp: float,
) -> TranscriptionChunkWindow | None:
    if not ordered_chunks:
        return None
    last_index = ordered_chunks[-1][0].index
    for window, _segments in ordered_chunks:
        if timestamp < window.ownership_start - 1e-9:
            continue
        if window.index == last_index:
            if timestamp <= window.ownership_end + 1e-9:
                return window
        elif timestamp < window.ownership_end - 1e-9:
            return window
    return None


def _phrase_occurrences(
    words: tuple[WordTiming, ...],
    phrase: tuple[str, ...],
    *,
    start: float,
    end: float,
    tolerance_seconds: float,
) -> list[tuple[int, int]]:
    tokens = tuple(_normalise_token(word.text) for word in words)
    results: list[tuple[int, int]] = []
    size = len(phrase)
    for index in range(0, len(words) - size + 1):
        if tokens[index : index + size] != phrase:
            continue
        occurrence = words[index : index + size]
        midpoint = (occurrence[0].start + occurrence[-1].end) / 2.0
        if midpoint < start - tolerance_seconds or midpoint > end + tolerance_seconds:
            continue
        results.append((index, index + size))
    return results


def _average_probability(words: tuple[WordTiming, ...]) -> float:
    values = [float(word.probability) for word in words if word.probability is not None]
    return sum(values) / len(values) if values else 0.0


def _segment_from_words(words: tuple[WordTiming, ...]) -> TranscriptSegment:
    return TranscriptSegment(
        text=" ".join(word.text for word in words).strip(),
        start=words[0].start,
        end=words[-1].end,
        words=words,
    )


def _replace_exact_word_sequence(
    segments: tuple[TranscriptSegment, ...],
    *,
    target: tuple[WordTiming, ...],
    replacement: tuple[WordTiming, ...],
) -> tuple[TranscriptSegment, ...] | None:
    """Replace one exact baseline word sequence without touching its context.

    The target objects must be the exact WordTiming instances already present in
    one baseline segment. Cross-segment or ambiguous matches fail closed.
    """
    if not target or not replacement:
        return None

    matches: list[tuple[int, int]] = []
    target_size = len(target)
    for segment_index, segment in enumerate(segments):
        for word_index in range(0, len(segment.words) - target_size + 1):
            candidate = segment.words[word_index : word_index + target_size]
            if all(current is expected for current, expected in zip(candidate, target)):
                matches.append((segment_index, word_index))

    if len(matches) != 1:
        return None

    segment_index, word_index = matches[0]
    rebuilt = list(segments)
    original = rebuilt[segment_index]
    words = (
        original.words[:word_index]
        + replacement
        + original.words[word_index + target_size :]
    )
    if not words:
        return None
    rebuilt[segment_index] = _segment_from_words(words)
    return tuple(rebuilt)


def merge_chunked_transcript_segments_with_repeat_consensus(
    chunks: Iterable[tuple[TranscriptionChunkWindow, tuple[TranscriptSegment, ...]]],
    *,
    timing_tolerance_seconds: float = REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
) -> tuple[TranscriptSegment, ...]:
    """Conservatively recover exact repetitions lost by deterministic ownership.

    The ordinary ownership merge remains the baseline. A reconstruction is
    allowed only when matching exact 3-7 token repetitions are independently
    present in one chunk before and one chunk after the temporal owner, their two
    occurrence timings agree, and the owner itself does not report that repeat.

    The baseline must contain exactly one lexical copy whose first word starts
    near the corroborated first occurrence and whose last word ends near the
    corroborated second occurrence. That is treated as a narrowly evidenced
    collapsed-span hypothesis. Only those exact baseline word objects are
    replaced by the corroborated repeated words; every surrounding baseline word
    is preserved unchanged. Otherwise this function returns the baseline
    unchanged for that region.

    This helper is Phase 2E hardening only. It does not authorize, approve or
    execute any edit and is not wired into the product default.
    """
    ordered = sorted(chunks, key=lambda item: (item[0].start, item[0].index))
    baseline = merge_chunked_transcript_segments(ordered)
    if len(ordered) < 3:
        return baseline

    by_window: dict[int, tuple[RepeatHypothesis, ...]] = {
        window.index: _repeat_hypotheses(window, segments)
        for window, segments in ordered
    }
    all_hypotheses = [
        hypothesis
        for hypotheses in by_window.values()
        for hypothesis in hypotheses
    ]
    if len(all_hypotheses) < 2:
        return baseline

    patched = baseline
    used_intervals: list[tuple[float, float]] = []
    for left_pos, left in enumerate(all_hypotheses):
        for right in all_hypotheses[left_pos + 1 :]:
            if left.window_index == right.window_index or left.phrase != right.phrase:
                continue
            if not _timings_agree(
                left,
                right,
                tolerance_seconds=timing_tolerance_seconds,
            ):
                continue

            first_start = (left.first_start + right.first_start) / 2.0
            first_end = (left.first_end + right.first_end) / 2.0
            second_start = (left.second_start + right.second_start) / 2.0
            second_end = (left.second_end + right.second_end) / 2.0
            owner = _owner_for_time(ordered, (first_start + first_end) / 2.0)
            if owner is None:
                continue
            supporter_indices = {left.window_index, right.window_index}
            if not (
                min(supporter_indices) < owner.index < max(supporter_indices)
            ):
                continue
            if any(
                item.phrase == left.phrase
                and _timings_agree(
                    item,
                    left,
                    tolerance_seconds=timing_tolerance_seconds,
                )
                for item in by_window.get(owner.index, ())
            ):
                continue

            interval_start = min(first_start, second_start)
            interval_end = max(first_end, second_end)
            if any(
                not (interval_end < used_start or interval_start > used_end)
                for used_start, used_end in used_intervals
            ):
                continue

            baseline_words = tuple(
                word
                for segment in patched
                for word in segment.words
                if interval_start - timing_tolerance_seconds
                <= (word.start + word.end) / 2.0
                <= interval_end + timing_tolerance_seconds
            )
            baseline_words = tuple(
                sorted(baseline_words, key=lambda item: (item.start, item.end, item.text))
            )
            occurrences = _phrase_occurrences(
                baseline_words,
                left.phrase,
                start=interval_start,
                end=interval_end,
                tolerance_seconds=timing_tolerance_seconds,
            )
            if len(occurrences) != 1:
                continue

            occurrence_start, occurrence_end = occurrences[0]
            collapsed_words = baseline_words[occurrence_start:occurrence_end]
            if not collapsed_words:
                continue
            if abs(float(collapsed_words[0].start) - first_start) > timing_tolerance_seconds:
                continue
            if abs(float(collapsed_words[-1].end) - second_end) > timing_tolerance_seconds:
                continue

            source = max(
                (left, right),
                key=lambda item: (_average_probability(item.words), -item.window_index),
            )
            rebuilt = _replace_exact_word_sequence(
                patched,
                target=collapsed_words,
                replacement=source.words,
            )
            if rebuilt is None:
                continue
            patched = rebuilt
            used_intervals.append((interval_start, interval_end))
            break

    return patched


def transcribe_audio_chunked_with_repeat_consensus(
    audio_wav: str | Path,
    *,
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
    window_seconds: float = CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    hop_seconds: float,
    strategy: str,
) -> TranscriptResult:
    """Run chunked Whisper and apply the Phase 2E repeat-consensus merge.

    This intentionally mirrors the established chunked decoder while leaving the
    generic ownership-only transcriber untouched. It is an internal evidence path
    until the human gate is re-run successfully.
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
            strategy=strategy,
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

    merged = merge_chunked_transcript_segments_with_repeat_consensus(chunk_results)
    return TranscriptResult(
        language=detected_language,
        language_probability=detected_probability,
        model=model_name,
        device=resolved_device,
        compute_type=resolved_compute,
        segments=merged,
        strategy=strategy,
        chunk_window_seconds=float(window_seconds),
        chunk_hop_seconds=float(hop_seconds),
        chunk_count=len(windows),
    )
