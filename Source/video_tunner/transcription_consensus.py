from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from .transcription import (
    TranscriptSegment,
    TranscriptionChunkWindow,
    WordTiming,
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


def _replace_interval(
    segments: tuple[TranscriptSegment, ...],
    *,
    start: float,
    end: float,
    replacement: tuple[WordTiming, ...],
) -> tuple[TranscriptSegment, ...]:
    rebuilt: list[TranscriptSegment] = []
    for segment in segments:
        before = tuple(
            word
            for word in segment.words
            if (word.start + word.end) / 2.0 < start - 1e-9
        )
        after = tuple(
            word
            for word in segment.words
            if (word.start + word.end) / 2.0 > end + 1e-9
        )
        if before:
            rebuilt.append(_segment_from_words(before))
        if after:
            rebuilt.append(_segment_from_words(after))
    rebuilt.append(_segment_from_words(replacement))
    rebuilt.sort(key=lambda item: (item.start, item.end, item.text))
    return tuple(rebuilt)


def merge_chunked_transcript_segments_with_repeat_consensus(
    chunks: Iterable[tuple[TranscriptionChunkWindow, tuple[TranscriptSegment, ...]]],
    *,
    timing_tolerance_seconds: float = REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
) -> tuple[TranscriptSegment, ...]:
    """Conservatively recover exact repetitions lost by deterministic ownership.

    The ordinary ownership merge remains the baseline. A replacement is allowed
    only when matching exact 3-7 token repetitions are independently present in
    one chunk before and one chunk after the temporal owner, their two occurrence
    timings agree, the owner itself does not report that repetition, and the
    baseline contains exactly one copy (and no other lexical material) across the
    corroborated repeated interval. Otherwise this function returns the baseline
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
            normalised_baseline = tuple(
                token
                for word in baseline_words
                if (token := _normalise_token(word.text))
            )
            if normalised_baseline != left.phrase:
                continue

            source = max(
                (left, right),
                key=lambda item: (_average_probability(item.words), -item.window_index),
            )
            replacement = source.words
            patched = _replace_interval(
                patched,
                start=interval_start - timing_tolerance_seconds,
                end=interval_end + timing_tolerance_seconds,
                replacement=replacement,
            )
            used_intervals.append((interval_start, interval_end))
            break

    return patched
