from __future__ import annotations

import re
import unicodedata
from typing import Any

from .transcription import TranscriptResult, WordTiming

SEMANTIC_SETTINGS = {
    "conservative": {
        "min_repeat_tokens": 3,
        "min_repeat_content_words": 1,
        "min_retake_prefix_tokens": 3,
        "max_retake_gap_seconds": 8.0,
        "max_intervening_tokens": 7,
        "reject_continuation_markers": True,
        "require_ambiguous_correction_evidence": True,
        "reject_apology_like_corrections": True,
    },
    "aggressive": {
        "min_repeat_tokens": 2,
        "min_repeat_content_words": 1,
        "min_retake_prefix_tokens": 2,
        "max_retake_gap_seconds": 8.0,
        "max_intervening_tokens": 9,
        "reject_continuation_markers": False,
        "require_ambiguous_correction_evidence": False,
        "reject_apology_like_corrections": False,
    },
}

# Deliberately small: these are candidate self-correction markers, not proof that
# a repair occurred. Human validation in Phase 2C showed that "I mean" and
# "perdón" can also be ordinary discourse/apology markers, so conservative mode
# requires additional local evidence for the ambiguous cases below.
CORRECTION_MARKERS: tuple[tuple[tuple[str, ...], float], ...] = (
    (("perdon",), 0.96),
    (("perdona",), 0.92),
    (("mejor", "dicho"), 0.92),
    (("quiero", "decir"), 0.78),
    (("sorry",), 0.90),
    (("i", "mean"), 0.78),
)

AMBIGUOUS_CORRECTION_MARKERS = {("quiero", "decir"), ("i", "mean")}
APOLOGY_CAPABLE_MARKERS = {("perdon",), ("perdona",), ("sorry",)}

# Small bilingual number-word set used only as a local replacement cue around
# ambiguous correction markers (e.g. "veinte - quiero decir treinta").
NUMBER_WORDS = {
    "cero", "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
    "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciseis",
    "diecisiete", "dieciocho", "diecinueve", "veinte", "treinta", "cuarenta", "cincuenta",
    "sesenta", "setenta", "ochenta", "noventa", "cien", "ciento", "mil",
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
    "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
    "eighty", "ninety", "hundred", "thousand",
}

# In real AMI audio, large-v3-turbo removed the manual truncation around
# "I just wondered - I mean h- how..." but preserved the reformulation as
# "I just wonder I mean how...". Interrogative reframing is therefore an
# ASR-surviving conservative cue. Keep the set narrow: Spanish "que" is excluded
# because it is usually a complementizer rather than an interrogative signal.
QUESTION_REFRAME_MARKERS = {
    "como", "cuando", "donde", "quien", "cual", "cuanto",
    "how", "what", "when", "where", "who", "which", "why",
}

# A compact bilingual stopword list is enough for the guardrail here: the goal
# is only to reject repetitions made entirely of connective tissue.
STOPWORDS = {
    "a", "al", "algo", "ante", "como", "con", "de", "del", "desde", "el", "ella",
    "en", "es", "esa", "ese", "esta", "este", "esto", "la", "las", "lo", "los", "me",
    "mi", "no", "o", "para", "pero", "por", "que", "se", "si", "sin", "su", "te", "tu",
    "un", "una", "uno", "y", "ya", "yo", "the", "a", "an", "and", "or", "but", "to",
    "of", "in", "on", "for", "with", "is", "it", "this", "that", "i", "you", "we",
}

# In conservative mode, a repeated opener separated by an ordinary continuation
# ("ahora y luego", "pero", "because"...) is more likely legitimate reuse than
# a retake. A nearby hesitation/repair marker overrides this rejection.
CONTINUATION_MARKERS = {
    "y", "pero", "porque", "luego", "despues", "ahora", "entonces", "mientras", "ademas",
    "and", "but", "because", "then", "later", "now", "while", "also", "however",
}
RETAKE_REPAIR_MARKERS = {
    "eh", "em", "erm", "er", "um", "umm", "uh", "uhh", "mmm", "mm", "hmm",
    "perdon", "perdona", "sorry",
}
HESITATION_MARKERS = {
    "eh", "em", "erm", "er", "um", "umm", "uh", "uhh", "mmm", "mm", "hmm",
}

MAX_REPEAT_TOKENS = 7
CONTEXT_WORDS = 7
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _all_words(transcript: TranscriptResult) -> list[WordTiming]:
    words = [word for segment in transcript.segments for word in segment.words]
    return sorted(words, key=lambda word: (word.start, word.end))


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _TOKEN_RE.sub("", asciiish)


def _tokens(words: list[WordTiming]) -> list[str]:
    return [_normalise(word.text) for word in words]


def _text(words: list[WordTiming]) -> str:
    return " ".join(word.text for word in words).strip()


def _content_word_count(tokens: list[str]) -> int:
    return sum(1 for token in tokens if token and token not in STOPWORDS and (len(token) >= 3 or token.isdigit()))


def _context(words: list[WordTiming], start: int, end: int) -> dict[str, str]:
    return {
        "context_before": _text(words[max(0, start - CONTEXT_WORDS):start]),
        "context_after": _text(words[end:min(len(words), end + CONTEXT_WORDS)]),
    }


def _candidate(
    words: list[WordTiming],
    *,
    kind: str,
    start: int,
    end: int,
    reason: str,
    confidence: float,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    span = words[start:end]
    if not span:
        raise ValueError("Un candidato semántico no puede tener un span vacío.")
    removed_text = _text(span)
    return {
        "id": "",
        "kind": kind,
        "start": round(span[0].start, 6),
        "end": round(span[-1].end, 6),
        "duration": round(max(0.0, span[-1].end - span[0].start), 6),
        "reason": reason,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "decision": "undecided",
        "suggested_decision": "REVIEW",
        "auto_apply": False,
        "evidence": {
            "detector": "deterministic-transcript-v1",
            "removed_text": removed_text,
            "word_start_index": start,
            "word_end_index_exclusive": end,
            "requires_semantic_review": True,
            "span_safe_for_auto_apply": False,
            **_context(words, start, end),
            **evidence,
        },
    }


def _ambiguous_marker_is_literal(tokens: list[str], index: int, marker: tuple[str, ...]) -> bool:
    if marker not in AMBIGUOUS_CORRECTION_MARKERS:
        return False
    if index == 0:
        return True
    left = tuple(token for token in tokens[max(0, index - 2):index] if token)
    if left[-2:] == ("lo", "que"):
        return True
    if left and left[-1] == "what":
        return True
    return False


def _repair_boundary_before(words: list[WordTiming], index: int) -> bool:
    """Return True for explicit transcript evidence of an interrupted attempt."""
    for word in words[max(0, index - 2):index]:
        raw = word.text.strip()
        if raw in {"-", "–", "—"}:
            return True
        if len(raw) > 1 and raw.endswith("-"):
            return True
    return False


def _numberish(token: str) -> bool:
    return bool(token) and (token.isdigit() or token in NUMBER_WORDS)


def _numeric_replacement_cue(tokens: list[str], index: int, end: int) -> bool:
    left = [token for token in tokens[max(0, index - 4):index] if token]
    right = [token for token in tokens[end:min(len(tokens), end + 4)] if token]
    return any(_numberish(token) for token in left) and any(_numberish(token) for token in right)


def _next_lexical_token(tokens: list[str], start: int) -> str:
    return next((token for token in tokens[start:] if token), "")


def _question_reframe_cue(tokens: list[str], index: int, end: int) -> bool:
    if not any(token for token in tokens[max(0, index - CONTEXT_WORDS):index]):
        return False
    return _next_lexical_token(tokens, end) in QUESTION_REFRAME_MARKERS


def _has_lexical_context(tokens: list[str], start: int, end: int) -> bool:
    return any(token for token in tokens[start:end])


def _find_correction_markers(
    words: list[WordTiming], tokens: list[str], *, settings: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    require_ambiguous_evidence = bool(settings.get("require_ambiguous_correction_evidence"))
    reject_apology_like = bool(settings.get("reject_apology_like_corrections"))

    for index in range(len(words)):
        for marker, confidence in CORRECTION_MARKERS:
            end = index + len(marker)
            if end > len(words) or tuple(tokens[index:end]) != marker:
                continue
            if _ambiguous_marker_is_literal(tokens, index, marker):
                continue

            repair_boundary = _repair_boundary_before(words, index)
            numeric_replacement = _numeric_replacement_cue(tokens, index, end)
            question_reframe = _question_reframe_cue(tokens, index, end)
            next_token = _next_lexical_token(tokens, end)
            has_left_context = _has_lexical_context(tokens, max(0, index - CONTEXT_WORDS), index)
            has_right_context = _has_lexical_context(tokens, end, min(len(tokens), end + CONTEXT_WORDS))

            if (
                marker in AMBIGUOUS_CORRECTION_MARKERS
                and require_ambiguous_evidence
                and not (repair_boundary or numeric_replacement or question_reframe)
            ):
                continue

            if marker in APOLOGY_CAPABLE_MARKERS and reject_apology_like:
                # At transcript edges there is not enough local evidence to call an
                # apology word a self-correction. Likewise, "perdón eh ..." without
                # an interrupted left attempt is conservatively treated as discourse.
                if not has_left_context or not has_right_context:
                    continue
                if next_token in HESITATION_MARKERS and not repair_boundary:
                    continue

            marker_text = _text(words[index:end])
            result.append(
                _candidate(
                    words,
                    kind="explicit_correction",
                    start=index,
                    end=end,
                    reason=(
                        "Marcador de posible autocorrección con evidencia local suficiente; "
                        "el alcance de la toma errónea requiere revisión semántica."
                    ),
                    confidence=confidence,
                    evidence={
                        "marker": marker_text,
                        "marker_normalized": " ".join(marker),
                        "span_scope": "marker_only",
                        "repair_boundary_before": repair_boundary,
                        "numeric_replacement_cue": numeric_replacement,
                        "question_reframe_cue": question_reframe,
                    },
                )
            )
            break
    return result


def _find_exact_repetitions(
    words: list[WordTiming], tokens: list[str], *, settings: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    used_first_starts: set[int] = set()
    minimum = int(settings["min_repeat_tokens"])
    min_content = int(settings["min_repeat_content_words"])

    for start in range(len(words)):
        if start in used_first_starts:
            continue
        max_size = min(MAX_REPEAT_TOKENS, (len(words) - start) // 2)
        for size in range(max_size, minimum - 1, -1):
            second = start + size
            phrase = tokens[start:second]
            if not all(phrase) or phrase != tokens[second:second + size]:
                continue
            if _content_word_count(phrase) < min_content:
                continue
            gap = words[second].start - words[second - 1].end
            if gap > float(settings["max_retake_gap_seconds"]):
                continue
            first_span = words[start:second]
            second_span = words[second:second + size]
            first_duration = max(0.0, first_span[-1].end - first_span[0].start)
            second_duration = max(0.0, second_span[-1].end - second_span[0].start)
            phrase_text = _text(first_span)
            confidence = 0.82 + min(0.14, 0.025 * size)
            result.append(
                _candidate(
                    words,
                    kind="possible_repetition",
                    start=start,
                    end=second,
                    reason="Frase adyacente repetida; se conserva intacta la segunda lectura.",
                    confidence=confidence,
                    evidence={
                        "first_occurrence_text": phrase_text,
                        "second_occurrence_text": _text(second_span),
                        "repeat_token_count": size,
                        "first_occurrence_seconds": round(first_duration, 6),
                        "second_occurrence_seconds": round(second_duration, 6),
                        "first_seconds_per_token": round(first_duration / size, 6),
                        "second_seconds_per_token": round(second_duration / size, 6),
                        "gap_to_second_seconds": round(max(0.0, gap), 6),
                        "keep_occurrence": "later",
                    },
                )
            )
            used_first_starts.add(start)
            break
    return result


def _common_prefix(tokens: list[str], first: int, second: int) -> int:
    size = 0
    while (
        first + size < len(tokens)
        and second + size < len(tokens)
        and size < MAX_REPEAT_TOKENS
        and tokens[first + size]
        and tokens[first + size] == tokens[second + size]
    ):
        size += 1
    return size


def _find_retake_openers(
    words: list[WordTiming], tokens: list[str], *, settings: dict[str, Any]
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    min_prefix = int(settings["min_retake_prefix_tokens"])
    min_content = int(settings["min_repeat_content_words"])
    max_intervening = int(settings["max_intervening_tokens"])
    max_gap = float(settings["max_retake_gap_seconds"])
    reject_continuations = bool(settings.get("reject_continuation_markers"))
    seen_pairs: set[tuple[int, int]] = set()

    for first in range(len(words)):
        second_limit = min(len(words), first + MAX_REPEAT_TOKENS + max_intervening + 1)
        for second in range(first + min_prefix + 1, second_limit):
            if words[second].start - words[first].start > max_gap:
                break
            prefix = _common_prefix(tokens, first, second)
            if prefix < min_prefix:
                continue
            # Only emit the left-maximal opener. Without this guard, one retake
            # also appears shifted by one or more words as suffix duplicates.
            if first > 0 and second > 0 and tokens[first - 1] and tokens[first - 1] == tokens[second - 1]:
                continue
            if _content_word_count(tokens[first:first + prefix]) < min_content:
                continue
            first_prefix_end = first + prefix
            intervening = second - first_prefix_end
            if intervening <= 0 or intervening > max_intervening:
                continue
            pair = (first, second)
            if pair in seen_pairs:
                continue

            between_tokens = [token for token in tokens[first_prefix_end:second] if token]
            repair_evidence = any(token in RETAKE_REPAIR_MARKERS for token in between_tokens)
            if (
                reject_continuations
                and not repair_evidence
                and any(token in CONTINUATION_MARKERS for token in between_tokens)
            ):
                continue

            seen_pairs.add(pair)
            repeated_text = _text(words[first:first + prefix])
            between_text = _text(words[first_prefix_end:second])
            confidence = 0.62 + min(0.20, prefix * 0.035) + (0.10 if repair_evidence else 0.0)
            result.append(
                _candidate(
                    words,
                    kind="possible_retake",
                    start=first,
                    end=second,
                    reason=(
                        "Inicio de frase repetido tras un intento intermedio; la segunda lectura "
                        "se mantiene fuera del span candidato."
                    ),
                    confidence=confidence,
                    evidence={
                        "repeated_opener_text": repeated_text,
                        "intervening_text": between_text,
                        "second_occurrence_text": _text(words[second:second + prefix]),
                        "prefix_token_count": prefix,
                        "intervening_token_count": intervening,
                        "repair_evidence": repair_evidence,
                        "keep_occurrence": "later",
                    },
                )
            )
    return result


def _deduplicate(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Prefer the more specific/high-confidence candidate when two heuristics emit
    # the exact same span. Different spans remain visible for later arbitration.
    by_span: dict[tuple[str, float, float], dict[str, Any]] = {}
    for candidate in candidates:
        key = (candidate["kind"], float(candidate["start"]), float(candidate["end"]))
        previous = by_span.get(key)
        if previous is None or float(candidate.get("confidence") or 0.0) > float(previous.get("confidence") or 0.0):
            by_span[key] = candidate
    return list(by_span.values())


def build_semantic_candidates(transcript: TranscriptResult, *, mode: str) -> list[dict[str, Any]]:
    """Return deterministic semantic candidates; never return executable edits.

    This pass intentionally detects only evidence that can be described from the
    word transcript itself. It does not decide meaning and never auto-applies.
    """
    if mode not in SEMANTIC_SETTINGS:
        raise ValueError(f"Modo desconocido: {mode}")
    words = _all_words(transcript)
    if not words:
        return []
    tokens = _tokens(words)
    settings = SEMANTIC_SETTINGS[mode]

    candidates = [
        *_find_correction_markers(words, tokens, settings=settings),
        *_find_exact_repetitions(words, tokens, settings=settings),
        *_find_retake_openers(words, tokens, settings=settings),
    ]
    candidates = _deduplicate(candidates)
    candidates.sort(key=lambda item: (float(item["start"]), float(item["end"]), item["kind"]))
    return candidates
