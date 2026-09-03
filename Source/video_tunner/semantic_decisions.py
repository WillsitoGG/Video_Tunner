from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any

from .transcription import TranscriptResult, WordTiming

CONTEXT_WORDS = 8
MIN_REPEAT_SECONDS_PER_TOKEN_FOR_PROPOSAL = 0.12
_TOKEN_RE = re.compile(r"[^a-z0-9%€$£.,+-]+")
_DIGIT_RE = re.compile(r"[+-]?(?:\d+[.,]?\d*|[.,]\d+)(?:%|€|\$|£)?")

NUMBER_WORDS = {
    "cero", "uno", "una", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
    "diez", "once", "doce", "trece", "catorce", "quince", "veinte", "treinta", "cuarenta",
    "cincuenta", "sesenta", "setenta", "ochenta", "noventa", "cien", "ciento", "mil", "millon",
    "millones", "billon", "billones", "zero", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "hundred", "thousand", "million", "billion",
}
UNIT_MARKERS = {
    "%", "porcentaje", "porcentajes", "percent", "pct", "euro", "euros", "dolar", "dolares", "dollar",
    "dollars", "libra", "libras", "pound", "pounds", "kg", "kilo", "kilos", "kilogramo", "kilogramos",
    "g", "gramo", "gramos", "l", "litro", "litros", "ml", "metro", "metros", "m", "km", "kilometro",
    "kilometros", "segundo", "segundos", "minuto", "minutos", "hora", "horas", "day", "days", "hour",
    "hours", "minute", "minutes", "second", "seconds", "meter", "meters", "kilometer", "kilometers",
}
NEGATIONS = {
    "no", "nunca", "jamas", "tampoco", "nadie", "ningun", "ninguno", "ninguna", "sin",
    "not", "never", "nobody", "none", "without", "neither", "nor",
}
PERSON_MARKERS = {
    "yo", "tu", "usted", "el", "ella", "nosotros", "nosotras", "vosotros", "vosotras", "ustedes",
    "me", "te", "nos", "os", "ellos", "ellas", "i", "you", "he", "she", "we", "they", "us",
}
TENSE_ASPECT_MARKERS = {
    "era", "eran", "fue", "fueron", "es", "son", "sera", "seran", "estaba", "estaban", "esta", "estan",
    "estara", "estaran", "habia", "habian", "ha", "han", "habra", "habran", "hice", "hizo", "hare",
    "haremos", "voy", "va", "vamos", "iba", "iban", "ayer", "hoy", "manana", "antes", "ahora", "despues",
    "was", "were", "is", "are", "will", "has", "have", "had", "did", "does", "today", "yesterday",
    "tomorrow", "before", "now", "after",
}
CONTRAST_CAUSAL_MARKERS = {
    "pero", "aunque", "porque", "sino", "excepto", "salvo", "entonces", "por", "tanto", "asi", "que",
    "but", "although", "because", "except", "unless", "therefore", "however", "so",
}
SAFE_FUMBLE_TOKENS = {
    "eh", "em", "erm", "er", "um", "umm", "uh", "uhh", "mmm", "mm", "hmm", "perdon", "perdona", "sorry",
}
SEMANTIC_KINDS = {"possible_repetition", "possible_retake", "explicit_correction"}


def _all_words(transcript: TranscriptResult) -> list[WordTiming]:
    return sorted(
        [word for segment in transcript.segments for word in segment.words],
        key=lambda word: (word.start, word.end),
    )


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _TOKEN_RE.sub("", asciiish).strip(".,")


def _normalised_phrase(text: str) -> list[str]:
    return [token for raw in text.split() if (token := _normalise(raw))]


def _text(words: list[WordTiming]) -> str:
    return " ".join(word.text for word in words).strip()


def _extract_number_features(words: list[WordTiming]) -> list[str]:
    values: list[str] = []
    for word in words:
        raw = word.text.strip()
        token = _normalise(raw)
        if _DIGIT_RE.search(raw) or token in NUMBER_WORDS:
            values.append(token or raw.lower())
    return values


def _extract_units(words: list[WordTiming]) -> list[str]:
    values: list[str] = []
    for word in words:
        raw = word.text.strip()
        token = _normalise(raw)
        if any(symbol in raw for symbol in ("%", "€", "$", "£")):
            values.append(next(symbol for symbol in ("%", "€", "$", "£") if symbol in raw))
        if token in UNIT_MARKERS:
            values.append(token)
    return values


def _tokens_from_set(words: list[WordTiming], vocabulary: set[str]) -> list[str]:
    return [token for word in words if (token := _normalise(word.text)) in vocabulary]


def _capitalised_entities(words: list[WordTiming]) -> list[str]:
    result: list[str] = []
    for index, word in enumerate(words):
        raw = word.text.strip(".,!?;:\"'()[]{}—-…")
        if not raw or index == 0:
            continue
        if raw[:1].isupper() and any(ch.isalpha() for ch in raw):
            result.append(raw)
    return result


def _features(words: list[WordTiming]) -> dict[str, list[str]]:
    return {
        "numbers": _extract_number_features(words),
        "units": _extract_units(words),
        "negations": _tokens_from_set(words, NEGATIONS),
        "person_markers": _tokens_from_set(words, PERSON_MARKERS),
        "tense_aspect_markers": _tokens_from_set(words, TENSE_ASPECT_MARKERS),
        "contrast_causal_markers": _tokens_from_set(words, CONTRAST_CAUSAL_MARKERS),
        "entity_like_tokens": _capitalised_entities(words),
    }


def _word_span_from_evidence(
    candidate: dict[str, Any], words: list[WordTiming]
) -> tuple[int, int] | None:
    evidence = candidate.get("evidence") or {}
    try:
        start = int(evidence["word_start_index"])
        end = int(evidence["word_end_index_exclusive"])
    except (KeyError, TypeError, ValueError):
        return None
    if start < 0 or end <= start or end > len(words):
        return None
    return start, end


def _validate_candidate_span(
    candidate: dict[str, Any], words: list[WordTiming]
) -> dict[str, Any]:
    span = _word_span_from_evidence(candidate, words)
    if span is None:
        return {
            "valid": False,
            "reason": "missing_or_invalid_word_span",
            "start_index": None,
            "end_index_exclusive": None,
            "transcript_text": "",
        }
    start, end = span
    transcript_text = _text(words[start:end])
    evidence_text = str((candidate.get("evidence") or {}).get("removed_text") or "").strip()
    text_matches = _normalised_phrase(transcript_text) == _normalised_phrase(evidence_text)
    candidate_start = float(candidate.get("start", -1.0))
    candidate_end = float(candidate.get("end", -1.0))
    timing_matches = (
        abs(candidate_start - words[start].start) <= 0.03
        and abs(candidate_end - words[end - 1].end) <= 0.03
    )
    return {
        "valid": text_matches and timing_matches,
        "reason": None if text_matches and timing_matches else "candidate_span_mismatch",
        "start_index": start,
        "end_index_exclusive": end,
        "transcript_text": transcript_text,
        "text_matches": text_matches,
        "timing_matches": timing_matches,
    }


def _feature_changes(before: dict[str, list[str]], after: dict[str, list[str]]) -> list[str]:
    changed: list[str] = []
    for key in before:
        if before[key] != after[key] and (before[key] or after[key]):
            changed.append(key)
    return changed


def _relation_windows(
    words: list[WordTiming], start: int, end: int
) -> tuple[list[WordTiming], list[WordTiming]]:
    return (
        words[max(0, start - CONTEXT_WORDS):start],
        words[end:min(len(words), end + CONTEXT_WORDS)],
    )


def _decision(
    candidate: dict[str, Any],
    *,
    index: int,
    decision: str,
    confidence: float,
    rationale: list[str],
    guard_status: str,
    span_validation: dict[str, Any],
    protections: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": f"semantic-decision-{index:04d}",
        "candidate_id": candidate["id"],
        "candidate_kind": candidate["kind"],
        "decision": decision,
        "confidence": round(max(0.0, min(1.0, confidence)), 4),
        "guard_status": guard_status,
        "executable": False,
        "auto_apply": False,
        "rationale": rationale,
        "proposed_span": {
            "start": candidate.get("start"),
            "end": candidate.get("end"),
            "removed_text": (candidate.get("evidence") or {}).get("removed_text"),
        },
        "span_validation": span_validation,
        "protections": protections,
    }


def build_semantic_decisions(
    transcript: TranscriptResult,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build non-executable semantic decisions with deterministic guardrails."""
    words = _all_words(transcript)
    decisions: list[dict[str, Any]] = []

    for candidate in candidates:
        if candidate.get("kind") not in SEMANTIC_KINDS:
            continue

        validation = _validate_candidate_span(candidate, words)
        if not validation["valid"]:
            decisions.append(
                _decision(
                    candidate,
                    index=len(decisions) + 1,
                    decision="KEEP",
                    confidence=1.0,
                    rationale=[
                        "El candidate no coincide exactamente con word indices/timestamps del transcript; fail-safe KEEP."
                    ],
                    guard_status="blocked",
                    span_validation=validation,
                    protections={"critical_changes": ["candidate_span_mismatch"]},
                )
            )
            continue

        start = int(validation["start_index"])
        end = int(validation["end_index_exclusive"])
        span_words = words[start:end]
        before_words, after_words = _relation_windows(words, start, end)
        span_features = _features(span_words)
        before_features = _features(before_words)
        after_features = _features(after_words)
        critical_changes = _feature_changes(before_features, after_features)
        protections = {
            "span": span_features,
            "context_before": before_features,
            "context_after": after_features,
            "critical_changes": critical_changes,
            "context_before_text": _text(before_words),
            "context_after_text": _text(after_words),
        }

        kind = str(candidate["kind"])
        evidence = candidate.get("evidence") or {}

        if kind == "possible_repetition":
            first = _normalised_phrase(str(evidence.get("first_occurrence_text") or ""))
            second = _normalised_phrase(str(evidence.get("second_occurrence_text") or ""))
            if not first or first != second:
                decisions.append(
                    _decision(
                        candidate,
                        index=len(decisions) + 1,
                        decision="REVIEW",
                        confidence=0.95,
                        rationale=["Las dos ocurrencias ya no son textualmente equivalentes tras normalización."],
                        guard_status="review",
                        span_validation=validation,
                        protections=protections,
                    )
                )
                continue

            first_rate = float(evidence.get("first_seconds_per_token") or 0.0)
            second_rate = float(evidence.get("second_seconds_per_token") or 0.0)
            timing_compressed = (
                first_rate <= 0.0
                or second_rate <= 0.0
                or min(first_rate, second_rate) < MIN_REPEAT_SECONDS_PER_TOKEN_FOR_PROPOSAL
            )
            protections["repeat_timing"] = {
                "first_seconds_per_token": first_rate,
                "second_seconds_per_token": second_rate,
                "minimum_for_proposal": MIN_REPEAT_SECONDS_PER_TOKEN_FOR_PROPOSAL,
                "compressed": timing_compressed,
            }
            if timing_compressed:
                decisions.append(
                    _decision(
                        candidate,
                        index=len(decisions) + 1,
                        decision="REVIEW",
                        confidence=max(0.9, float(candidate.get("confidence") or 0.8)),
                        rationale=[
                            "La repetición es textualmente exacta, pero sus timestamps están anómalamente comprimidos.",
                            "El audio real demostró que Whisper puede omitir una vacilación y fabricar adyacencia textual; fail-safe REVIEW.",
                        ],
                        guard_status="review",
                        span_validation=validation,
                        protections=protections,
                    )
                )
                continue

            decisions.append(
                _decision(
                    candidate,
                    index=len(decisions) + 1,
                    decision="PROPOSED_CUT",
                    confidence=min(0.95, float(candidate.get("confidence") or 0.8)),
                    rationale=[
                        "Repetición adyacente exacta; la ocurrencia posterior equivalente queda fuera del span propuesto.",
                        "La propuesta sigue siendo no ejecutable hasta validar joins/corpus real.",
                    ],
                    guard_status="pass",
                    span_validation=validation,
                    protections=protections,
                )
            )
            continue

        if kind == "possible_retake":
            intervening = _normalised_phrase(str(evidence.get("intervening_text") or ""))
            unsafe_intervening = [token for token in intervening if token not in SAFE_FUMBLE_TOKENS]
            if unsafe_intervening or critical_changes:
                rationale = ["La retoma contiene material que no puede declararse descartable de forma determinista."]
                if unsafe_intervening:
                    rationale.append("Tokens intermedios no triviales: " + " ".join(unsafe_intervening))
                if critical_changes:
                    rationale.append("Cambios protegidos entre contexto anterior/posterior: " + ", ".join(critical_changes))
                decisions.append(
                    _decision(
                        candidate,
                        index=len(decisions) + 1,
                        decision="REVIEW",
                        confidence=max(0.7, float(candidate.get("confidence") or 0.7)),
                        rationale=rationale,
                        guard_status="review",
                        span_validation=validation,
                        protections=protections,
                    )
                )
            else:
                decisions.append(
                    _decision(
                        candidate,
                        index=len(decisions) + 1,
                        decision="PROPOSED_CUT",
                        confidence=min(0.9, float(candidate.get("confidence") or 0.75)),
                        rationale=[
                            "El material entre openers repetidos contiene sólo tokens de vacilación/corrección permitidos.",
                            "La segunda lectura queda fuera del span; propuesta todavía no ejecutable.",
                        ],
                        guard_status="pass",
                        span_validation=validation,
                        protections=protections,
                    )
                )
            continue

        # explicit_correction: marker detection is strong evidence of a correction
        # event, but not of the exact wrong-take boundary.
        rationale = [
            "Marcador explícito de autocorrección detectado; el límite de la toma errónea no está demostrado.",
        ]
        if critical_changes:
            rationale.append(
                "Hay rasgos protegidos diferentes a ambos lados del marcador: " + ", ".join(critical_changes)
            )
        protections["correction_relation"] = {
            "attempt_window_text": _text(before_words),
            "corrected_window_text": _text(after_words),
            "changed_features": critical_changes,
            "critical": any(
                feature in critical_changes
                for feature in ("numbers", "units", "negations", "person_markers", "tense_aspect_markers")
            ),
        }
        decisions.append(
            _decision(
                candidate,
                index=len(decisions) + 1,
                decision="REVIEW",
                confidence=max(0.9, float(candidate.get("confidence") or 0.9)),
                rationale=rationale,
                guard_status="review",
                span_validation=validation,
                protections=protections,
            )
        )

    return decisions


def semantic_decision_summary(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(item["decision"] for item in decisions)
    guards = Counter(item["guard_status"] for item in decisions)
    return {
        "count": len(decisions),
        "by_decision": dict(sorted(counts.items())),
        "by_guard_status": dict(sorted(guards.items())),
        "executable": sum(1 for item in decisions if item.get("executable")),
        "auto_apply": sum(1 for item in decisions if item.get("auto_apply")),
    }
