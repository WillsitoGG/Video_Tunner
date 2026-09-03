from __future__ import annotations

import re
import unicodedata
from typing import Any

from .semantic_decisions import (
    CONTRAST_CAUSAL_MARKERS,
    NEGATIONS,
    NUMBER_WORDS,
    PERSON_MARKERS,
    TENSE_ASPECT_MARKERS,
    UNIT_MARKERS,
)
from .transcription import TranscriptResult, WordTiming

STRONG_BOUNDARY_ENDINGS = (".", "?", "!", ";")
JOIN_CRITICAL_WINDOW = 2
SPAN_TOLERANCE_SECONDS = 0.03
_TOKEN_RE = re.compile(r"[^a-z0-9%€$£.,+-]+")
_DIGIT_RE = re.compile(r"[+-]?(?:\d+[.,]?\d*|[.,]\d+)(?:%|€|\$|£)?")


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _TOKEN_RE.sub("", asciiish).strip(".,")


def _normalised_phrase(text: str) -> list[str]:
    return [token for raw in text.split() if (token := _normalise(raw))]


def _flatten_words(transcript: TranscriptResult) -> tuple[list[WordTiming], list[int]]:
    pairs: list[tuple[WordTiming, int]] = []
    for segment_index, segment in enumerate(transcript.segments):
        for word in segment.words:
            pairs.append((word, segment_index))
    pairs.sort(key=lambda item: (item[0].start, item[0].end))
    return [item[0] for item in pairs], [item[1] for item in pairs]


def _text(words: list[WordTiming]) -> str:
    return " ".join(word.text for word in words).strip()


def _word_record(word: WordTiming | None, index: int | None, segment_index: int | None) -> dict[str, Any] | None:
    if word is None or index is None or segment_index is None:
        return None
    return {
        "word_index": index,
        "segment_index": segment_index,
        "text": word.text,
        "start": round(word.start, 6),
        "end": round(word.end, 6),
        "probability": word.probability,
    }


def _span_from_candidate(candidate: dict[str, Any], words: list[WordTiming]) -> dict[str, Any] | None:
    evidence = candidate.get("evidence") or {}
    try:
        start = int(evidence["word_start_index"])
        end = int(evidence["word_end_index_exclusive"])
    except (KeyError, TypeError, ValueError):
        return None
    if start < 0 or end <= start or end > len(words):
        return None
    selected = words[start:end]
    transcript_text = _text(selected)
    evidence_text = str(evidence.get("removed_text") or "").strip()
    if _normalised_phrase(transcript_text) != _normalised_phrase(evidence_text):
        return None
    try:
        candidate_start = float(candidate["start"])
        candidate_end = float(candidate["end"])
    except (KeyError, TypeError, ValueError):
        return None
    if (
        abs(candidate_start - selected[0].start) > SPAN_TOLERANCE_SECONDS
        or abs(candidate_end - selected[-1].end) > SPAN_TOLERANCE_SECONDS
    ):
        return None
    return {
        "start_index": start,
        "end_index_exclusive": end,
        "start": float(selected[0].start),
        "end": float(selected[-1].end),
        "text": transcript_text,
        "source": "candidate_word_span",
    }


def _span_from_filler_candidate(candidate: dict[str, Any], words: list[WordTiming]) -> dict[str, Any] | None:
    try:
        candidate_start = float(candidate["start"])
        candidate_end = float(candidate["end"])
    except (KeyError, TypeError, ValueError):
        return None
    token = str((candidate.get("evidence") or {}).get("token") or "")
    matches = [
        index
        for index, word in enumerate(words)
        if abs(word.start - candidate_start) <= SPAN_TOLERANCE_SECONDS
        and abs(word.end - candidate_end) <= SPAN_TOLERANCE_SECONDS
        and (not token or _normalise(word.text) == _normalise(token))
    ]
    if len(matches) != 1:
        return None
    index = matches[0]
    return {
        "start_index": index,
        "end_index_exclusive": index + 1,
        "start": float(words[index].start),
        "end": float(words[index].end),
        "text": words[index].text,
        "source": "filler_word_timing_match",
    }


def _span_from_correction_scope(
    candidate_id: str,
    correction_scopes: list[dict[str, Any]],
    words: list[WordTiming],
) -> dict[str, Any] | None:
    scope = next(
        (
            item
            for item in correction_scopes
            if item.get("candidate_id") == candidate_id and item.get("status") == "bounded"
        ),
        None,
    )
    if scope is None:
        return None
    attempt = scope.get("attempt_span") or {}
    marker = scope.get("marker_span") or {}
    try:
        start = int(attempt["word_start_index"])
        marker_start = int(marker["word_start_index"])
        end = int(marker["word_end_index_exclusive"])
    except (KeyError, TypeError, ValueError):
        return None
    if start < 0 or marker_start < start or end <= marker_start or end > len(words):
        return None
    if _normalised_phrase(_text(words[start:marker_start])) != _normalised_phrase(str(attempt.get("text") or "")):
        return None
    if _normalised_phrase(_text(words[marker_start:end])) != _normalised_phrase(str(marker.get("text") or "")):
        return None
    return {
        "start_index": start,
        "end_index_exclusive": end,
        "start": float(words[start].start),
        "end": float(words[end - 1].end),
        "text": _text(words[start:end]),
        "source": "bounded_correction_attempt_plus_marker",
    }


def _pause_neighbors(
    candidate: dict[str, Any], words: list[WordTiming]
) -> tuple[int | None, int | None]:
    try:
        start = float(candidate["start"])
        end = float(candidate["end"])
    except (KeyError, TypeError, ValueError):
        return None, None
    if start < 0 or end <= start:
        return None, None
    left = None
    right = None
    for index, word in enumerate(words):
        if word.end <= start + SPAN_TOLERANCE_SECONDS:
            left = index
            continue
        if word.start >= end - SPAN_TOLERANCE_SECONDS:
            right = index
            break
    return left, right


def _critical_token_features(words: list[WordTiming]) -> dict[str, list[str]]:
    features: dict[str, list[str]] = {
        "numbers": [],
        "units": [],
        "negations": [],
        "person_markers": [],
        "tense_aspect_markers": [],
        "contrast_causal_markers": [],
    }
    for word in words:
        raw = word.text.strip()
        token = _normalise(raw)
        if _DIGIT_RE.search(raw) or token in NUMBER_WORDS:
            features["numbers"].append(token or raw.lower())
        if any(symbol in raw for symbol in ("%", "€", "$", "£")) or token in UNIT_MARKERS:
            features["units"].append(token or raw.lower())
        if token in NEGATIONS:
            features["negations"].append(token)
        if token in PERSON_MARKERS:
            features["person_markers"].append(token)
        if token in TENSE_ASPECT_MARKERS:
            features["tense_aspect_markers"].append(token)
        if token in CONTRAST_CAUSAL_MARKERS:
            features["contrast_causal_markers"].append(token)
    return features


def _has_critical_features(features: dict[str, list[str]]) -> bool:
    return any(bool(values) for values in features.values())


def _strong_punctuation_boundary(left: WordTiming, right: WordTiming) -> bool:
    return left.text.rstrip().endswith(STRONG_BOUNDARY_ENDINGS) or right.text.lstrip().startswith(("¿", "¡"))


def _assessment(
    candidate: dict[str, Any],
    *,
    status: str,
    rationale: list[str],
    target_span: dict[str, Any] | None,
    left: dict[str, Any] | None,
    right: dict[str, Any] | None,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": "",
        "candidate_id": candidate.get("id"),
        "candidate_kind": candidate.get("kind"),
        "status": status,
        "rationale": rationale,
        "target_span": target_span,
        "left_context": left,
        "right_context": right,
        "evidence": evidence,
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def build_join_assessments(
    transcript: TranscriptResult,
    candidates: list[dict[str, Any]],
    *,
    correction_scopes: list[dict[str, Any]] | None = None,
    filler_assessments: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Describe the two sides of hypothetical joins without authorizing a cut.

    This layer is deliberately conservative. It records boundary/risk evidence
    for existing candidates but every assessment remains non-executable and
    unsafe-for-cut during Phase 2D.3 foundation.
    """
    correction_scopes = correction_scopes or []
    filler_assessments = filler_assessments or []
    words, segment_indexes = _flatten_words(transcript)
    results: list[dict[str, Any]] = []

    for candidate in candidates:
        kind = str(candidate.get("kind") or "")
        if kind not in {
            "pause",
            "possible_filler",
            "possible_repetition",
            "possible_retake",
            "explicit_correction",
        }:
            continue

        target_span: dict[str, Any] | None = None
        left_index: int | None = None
        right_index: int | None = None

        if kind == "pause":
            left_index, right_index = _pause_neighbors(candidate, words)
            if left_index is not None and right_index is not None:
                target_span = {
                    "start_index": None,
                    "end_index_exclusive": None,
                    "start": float(candidate["start"]),
                    "end": float(candidate["end"]),
                    "text": "",
                    "source": "candidate_temporal_gap",
                }
        elif kind == "possible_filler":
            target_span = _span_from_filler_candidate(candidate, words)
            if target_span is not None:
                left_index = int(target_span["start_index"]) - 1
                right_index = int(target_span["end_index_exclusive"])
        elif kind == "explicit_correction":
            target_span = _span_from_correction_scope(str(candidate.get("id") or ""), correction_scopes, words)
            if target_span is not None:
                left_index = int(target_span["start_index"]) - 1
                right_index = int(target_span["end_index_exclusive"])
        else:
            target_span = _span_from_candidate(candidate, words)
            if target_span is not None:
                left_index = int(target_span["start_index"]) - 1
                right_index = int(target_span["end_index_exclusive"])

        if target_span is None:
            results.append(
                _assessment(
                    candidate,
                    status="invalid_or_unbounded_target",
                    rationale=[
                        "No existe un target span íntegro y suficientemente acotado para evaluar el join; fail-safe."
                    ],
                    target_span=None,
                    left=None,
                    right=None,
                    evidence={"target_resolved": False},
                )
            )
            continue

        left_valid = left_index is not None and 0 <= left_index < len(words)
        right_valid = right_index is not None and 0 <= right_index < len(words)
        if not left_valid or not right_valid:
            left_record = (
                _word_record(words[left_index], left_index, segment_indexes[left_index]) if left_valid else None
            )
            right_record = (
                _word_record(words[right_index], right_index, segment_indexes[right_index]) if right_valid else None
            )
            results.append(
                _assessment(
                    candidate,
                    status="transcript_edge",
                    rationale=["El span toca un borde del transcript y no tiene contexto bilateral."],
                    target_span=target_span,
                    left=left_record,
                    right=right_record,
                    evidence={"target_resolved": True, "bilateral_context": False},
                )
            )
            continue

        assert left_index is not None and right_index is not None
        left_word = words[left_index]
        right_word = words[right_index]
        left_segment = segment_indexes[left_index]
        right_segment = segment_indexes[right_index]
        left_window = words[max(0, left_index - JOIN_CRITICAL_WINDOW + 1):left_index + 1]
        right_window = words[right_index:min(len(words), right_index + JOIN_CRITICAL_WINDOW)]
        left_features = _critical_token_features(left_window)
        right_features = _critical_token_features(right_window)
        critical = _has_critical_features(left_features) or _has_critical_features(right_features)
        segment_boundary = left_segment != right_segment
        punctuation_boundary = _strong_punctuation_boundary(left_word, right_word)

        filler_context = next(
            (item for item in filler_assessments if item.get("candidate_id") == candidate.get("id")),
            None,
        )
        protected_filler = filler_context is not None and filler_context.get("status") in {
            "protected_repair_context",
            "hesitation_cluster",
            "boundary_hesitation",
            "uncertain_asr",
            "invalid",
        }
        repair_kind = kind in {"possible_retake", "explicit_correction"}

        if repair_kind or protected_filler:
            status = "repair_or_protected_context_risk"
            rationale = [
                "El target participa en una reparación o contexto de filler protegido; no evaluar como join ordinario."
            ]
        elif critical:
            status = "critical_lexical_context_risk"
            rationale = [
                "Hay cifras/unidades/negación/persona/tiempo/causalidad junto al join hipotético."
            ]
        elif segment_boundary:
            status = "segment_boundary_risk"
            rationale = [
                "Los lados del join pertenecen a segmentos ASR distintos; esta frontera no debe colapsarse sin revisión."
            ]
        elif punctuation_boundary:
            status = "sentence_boundary_risk"
            rationale = [
                "La puntuación ASR aporta una señal de posible frontera de frase; se conserva como riesgo, no como verdad absoluta."
            ]
        else:
            status = "join_context_only"
            rationale = [
                "Hay contexto léxico bilateral sin una guarda de riesgo v1 activada; sigue siendo sólo evidencia no ejecutable."
            ]

        target_start = float(target_span["start"])
        target_end = float(target_span["end"])
        evidence = {
            "target_resolved": True,
            "bilateral_context": True,
            "left_gap_to_target_seconds": round(max(0.0, target_start - left_word.end), 6),
            "right_gap_from_target_seconds": round(max(0.0, right_word.start - target_end), 6),
            "target_duration_seconds": round(max(0.0, target_end - target_start), 6),
            "segment_boundary": segment_boundary,
            "punctuation_boundary": punctuation_boundary,
            "critical_features_left": left_features,
            "critical_features_right": right_features,
            "repair_kind": repair_kind,
            "filler_context_status": None if filler_context is None else filler_context.get("status"),
        }
        results.append(
            _assessment(
                candidate,
                status=status,
                rationale=rationale,
                target_span=target_span,
                left=_word_record(left_word, left_index, left_segment),
                right=_word_record(right_word, right_index, right_segment),
                evidence=evidence,
            )
        )

    for index, item in enumerate(results, start=1):
        item["id"] = f"join-assessment-{index:04d}"
    return results
