from __future__ import annotations

import re
import unicodedata
from typing import Any

from .transcription import TranscriptResult, WordTiming

_SCOPE_CONTEXT_WORDS = 8
_TOKEN_RE = re.compile(r"[^a-z0-9%€$£.,+-]+")
_DIGIT_RE = re.compile(r"[+-]?(?:\d+[.,]?\d*|[.,]\d+)(?:%|€|\$|£)?")

NUMBER_WORDS = {
    "cero", "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "veinte", "treinta", "cuarenta",
    "cincuenta", "sesenta", "setenta", "ochenta", "noventa", "cien", "ciento", "mil",
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "hundred", "thousand", "million", "billion",
}


def _all_words(transcript: TranscriptResult) -> list[WordTiming]:
    return sorted(
        [word for segment in transcript.segments for word in segment.words],
        key=lambda word: (word.start, word.end),
    )


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _TOKEN_RE.sub("", asciiish).strip(".,")


def _text(words: list[WordTiming]) -> str:
    return " ".join(word.text for word in words).strip()


def _span(words: list[WordTiming], start: int, end: int) -> dict[str, Any] | None:
    if start < 0 or end <= start or end > len(words):
        return None
    selected = words[start:end]
    return {
        "word_start_index": start,
        "word_end_index_exclusive": end,
        "start": round(selected[0].start, 6),
        "end": round(selected[-1].end, 6),
        "text": _text(selected),
    }


def _numberish(raw: str) -> bool:
    token = _normalise(raw)
    return bool(_DIGIT_RE.search(raw) or token in NUMBER_WORDS)


def _latest_repeated_anchor(
    words: list[WordTiming], marker_start: int, marker_end: int
) -> tuple[int, int] | None:
    """Find a short corrected-prefix anchor repeated immediately before the marker."""
    right_tokens = [_normalise(word.text) for word in words[marker_end:marker_end + 4]]
    right_tokens = [token for token in right_tokens if token]
    if not right_tokens:
        return None

    left_start = max(0, marker_start - _SCOPE_CONTEXT_WORDS)
    left_tokens = [_normalise(word.text) for word in words[left_start:marker_start]]

    # Prefer a longer corrected-prefix anchor, then the latest matching location.
    max_anchor = min(3, len(right_tokens))
    for size in range(max_anchor, 0, -1):
        target = right_tokens[:size]
        for relative in range(len(left_tokens) - size, -1, -1):
            if left_tokens[relative:relative + size] != target:
                continue
            attempt_start = left_start + relative
            # The attempt must contain material beyond the repeated anchor;
            # otherwise this is just a marker between identical connective words.
            if marker_start - (attempt_start + size) < 1:
                continue
            return attempt_start, size
    return None


def _numeric_attempt_start(words: list[WordTiming], marker_start: int, marker_end: int) -> int | None:
    left = range(max(0, marker_start - 4), marker_start)
    right = range(marker_end, min(len(words), marker_end + 4))
    if not any(_numberish(words[index].text) for index in right):
        return None
    for index in reversed(list(left)):
        if _numberish(words[index].text):
            return index
    return None


def resolve_correction_scope(
    words: list[WordTiming], *, marker_start: int, marker_end: int
) -> dict[str, Any]:
    """Resolve a non-executable candidate scope for an explicit correction.

    `bounded` means a deterministic local left boundary was found. It does not
    mean the span is safe to cut. `ambiguous` means the correction event may be
    real while its prior wrong-take boundary remains unproven.
    """
    marker_span = _span(words, marker_start, marker_end)
    corrected_window_end = min(len(words), marker_end + _SCOPE_CONTEXT_WORDS)
    corrected_window = _span(words, marker_end, corrected_window_end)

    if marker_span is None:
        return {
            "status": "invalid",
            "strategy": "invalid_marker_span",
            "confidence": 0.0,
            "attempt_span": None,
            "marker_span": None,
            "corrected_window": corrected_window,
            "safe_for_cut": False,
            "executable": False,
            "auto_apply": False,
            "reason": ["El span del marcador no es válido."],
        }

    repeated = _latest_repeated_anchor(words, marker_start, marker_end)
    if repeated is not None:
        attempt_start, anchor_size = repeated
        return {
            "status": "bounded",
            "strategy": "repeated_corrected_prefix_anchor",
            "confidence": 0.82,
            "attempt_span": _span(words, attempt_start, marker_start),
            "marker_span": marker_span,
            "corrected_window": corrected_window,
            "anchor_token_count": anchor_size,
            "safe_for_cut": False,
            "executable": False,
            "auto_apply": False,
            "reason": [
                "El inicio de la formulación corregida reaparece antes del marcador y acota un intento previo.",
                "El scope es evidencia no ejecutable; todavía requiere join/sentence safety.",
            ],
        }

    numeric_start = _numeric_attempt_start(words, marker_start, marker_end)
    if numeric_start is not None:
        return {
            "status": "bounded",
            "strategy": "local_numeric_replacement",
            "confidence": 0.78,
            "attempt_span": _span(words, numeric_start, marker_start),
            "marker_span": marker_span,
            "corrected_window": corrected_window,
            "anchor_token_count": 0,
            "safe_for_cut": False,
            "executable": False,
            "auto_apply": False,
            "reason": [
                "Hay una sustitución numérica local a ambos lados del marcador; se acota sólo el valor previo.",
                "El scope es evidencia no ejecutable y no autoriza un corte.",
            ],
        }

    return {
        "status": "ambiguous",
        "strategy": "no_deterministic_left_boundary",
        "confidence": 0.0,
        "attempt_span": None,
        "marker_span": marker_span,
        "corrected_window": corrected_window,
        "anchor_token_count": 0,
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
        "reason": [
            "La corrección puede ser real, pero no existe una frontera izquierda determinista suficiente.",
            "Fail-safe: conservar marker-only y mantener REVIEW.",
        ],
    }


def build_correction_scopes(
    transcript: TranscriptResult, candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build scope evidence for explicit corrections without creating edits."""
    words = _all_words(transcript)
    scopes: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("kind") != "explicit_correction":
            continue
        evidence = candidate.get("evidence") or {}
        try:
            marker_start = int(evidence["word_start_index"])
            marker_end = int(evidence["word_end_index_exclusive"])
        except (KeyError, TypeError, ValueError):
            marker_start = -1
            marker_end = -1

        scope = resolve_correction_scope(words, marker_start=marker_start, marker_end=marker_end)
        scopes.append(
            {
                "id": f"correction-scope-{len(scopes) + 1:04d}",
                "candidate_id": candidate.get("id"),
                "candidate_kind": candidate.get("kind"),
                **scope,
            }
        )
    return scopes
