from __future__ import annotations

from typing import Any

from .transcription import TranscriptResult, WordTiming

WORD_MATCH_TOLERANCE_SECONDS = 0.03
REPAIR_NEARBY_SECONDS = 0.40
BOUNDARY_GAP_SECONDS = 0.60
LOW_ASR_PROBABILITY = 0.60
FILLER_KIND = "possible_filler"
SEMANTIC_REPAIR_KINDS = {"possible_retake", "explicit_correction"}


def _all_words(transcript: TranscriptResult) -> list[WordTiming]:
    return sorted(
        [word for segment in transcript.segments for word in segment.words],
        key=lambda word: (word.start, word.end),
    )


def _normalise(text: str) -> str:
    return text.lower().strip(".,!?;:\"'()[]{}—-…")


def _find_word_index(candidate: dict[str, Any], words: list[WordTiming]) -> int | None:
    token = _normalise(str((candidate.get("evidence") or {}).get("token") or ""))
    start = float(candidate.get("start", -1.0))
    end = float(candidate.get("end", -1.0))
    for index, word in enumerate(words):
        if token and _normalise(word.text) != token:
            continue
        if abs(word.start - start) <= WORD_MATCH_TOLERANCE_SECONDS and abs(word.end - end) <= WORD_MATCH_TOLERANCE_SECONDS:
            return index
    return None


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _repair_links(candidate: dict[str, Any], candidates: list[dict[str, Any]]) -> list[str]:
    start = float(candidate["start"])
    end = float(candidate["end"])
    duration = max(0.001, end - start)
    links: list[str] = []
    for other in candidates:
        if other is candidate or other.get("kind") not in SEMANTIC_REPAIR_KINDS:
            continue
        other_start = float(other.get("start", -1.0))
        other_end = float(other.get("end", -1.0))
        overlap = _overlap(start, end, other_start, other_end)
        nearby = min(abs(start - other_end), abs(other_start - end))
        if overlap >= duration * 0.5 or nearby <= REPAIR_NEARBY_SECONDS:
            links.append(str(other.get("id") or other.get("kind")))
    return sorted(set(links))


def _neighbor_context(words: list[WordTiming], index: int) -> dict[str, Any]:
    current = words[index]
    previous = words[index - 1] if index > 0 else None
    following = words[index + 1] if index + 1 < len(words) else None
    gap_before = None if previous is None else max(0.0, current.start - previous.end)
    gap_after = None if following is None else max(0.0, following.start - current.end)
    return {
        "word_index": index,
        "token": current.text,
        "probability": current.probability,
        "before_word": None if previous is None else previous.text,
        "after_word": None if following is None else following.text,
        "gap_before_seconds": None if gap_before is None else round(gap_before, 6),
        "gap_after_seconds": None if gap_after is None else round(gap_after, 6),
        "at_transcript_boundary": previous is None or following is None,
    }


def _is_filler_word(word: WordTiming, filler_tokens: set[str]) -> bool:
    return _normalise(word.text) in filler_tokens


def assess_filler_context(
    transcript: TranscriptResult,
    candidates: list[dict[str, Any]],
    filler_candidate: dict[str, Any],
) -> dict[str, Any]:
    """Classify contextual evidence for one filler candidate without authorizing edits."""
    words = _all_words(transcript)
    word_index = _find_word_index(filler_candidate, words)
    base = {
        "candidate_id": filler_candidate.get("id"),
        "candidate_kind": filler_candidate.get("kind"),
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }
    if word_index is None:
        return {
            **base,
            "status": "invalid",
            "confidence": 0.0,
            "context": None,
            "repair_candidate_ids": [],
            "reason": ["No se puede vincular el filler candidate a un word timing exacto; fail-safe invalid."],
        }

    context = _neighbor_context(words, word_index)
    repair_ids = _repair_links(filler_candidate, candidates)
    if repair_ids:
        return {
            **base,
            "status": "protected_repair_context",
            "confidence": 0.95,
            "context": context,
            "repair_candidate_ids": repair_ids,
            "reason": [
                "La vacilación está dentro o junto a una retoma/autocorrección detectada.",
                "No se evalúa como filler aislado hasta resolver el evento de reparación completo.",
            ],
        }

    probability = context.get("probability")
    if probability is None or float(probability) < LOW_ASR_PROBABILITY:
        return {
            **base,
            "status": "uncertain_asr",
            "confidence": 0.0 if probability is None else round(float(probability), 4),
            "context": context,
            "repair_candidate_ids": [],
            "reason": ["La evidencia ASR del token es insuficiente para valorar su eliminabilidad."],
        }

    filler_tokens = {
        _normalise(str((item.get("evidence") or {}).get("token") or ""))
        for item in candidates
        if item.get("kind") == FILLER_KIND
    }
    previous = words[word_index - 1] if word_index > 0 else None
    following = words[word_index + 1] if word_index + 1 < len(words) else None
    if (
        (previous is not None and _is_filler_word(previous, filler_tokens))
        or (following is not None and _is_filler_word(following, filler_tokens))
    ):
        return {
            **base,
            "status": "hesitation_cluster",
            "confidence": 0.85,
            "context": context,
            "repair_candidate_ids": [],
            "reason": [
                "El token forma parte de un cluster de vacilaciones vocales.",
                "El cluster requiere evaluación conjunta; no cortar tokens individualmente todavía.",
            ],
        }

    gap_before = context.get("gap_before_seconds")
    gap_after = context.get("gap_after_seconds")
    if (
        context["at_transcript_boundary"]
        or (gap_before is not None and float(gap_before) >= BOUNDARY_GAP_SECONDS)
        or (gap_after is not None and float(gap_after) >= BOUNDARY_GAP_SECONDS)
    ):
        return {
            **base,
            "status": "boundary_hesitation",
            "confidence": 0.75,
            "context": context,
            "repair_candidate_ids": [],
            "reason": [
                "La vacilación está en un boundary o junto a una pausa amplia.",
                "Puede afectar ritmo/turno; conservar para revisión hasta sentence/join safety.",
            ],
        }

    return {
        **base,
        "status": "isolated_hesitation",
        "confidence": 0.80,
        "context": context,
        "repair_candidate_ids": [],
        "reason": [
            "Vacilación vocal aislada con contexto léxico a ambos lados y ASR suficiente.",
            "Es una señal contextual para revisión, no una autorización de corte.",
        ],
    }


def build_filler_assessments(
    transcript: TranscriptResult, candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Build a non-executable contextual assessment for every filler candidate."""
    assessments: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("kind") != FILLER_KIND:
            continue
        assessment = assess_filler_context(transcript, candidates, candidate)
        assessments.append(
            {
                "id": f"filler-assessment-{len(assessments) + 1:04d}",
                **assessment,
            }
        )
    return assessments
