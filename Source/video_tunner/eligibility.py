from __future__ import annotations

import re
import unicodedata
from typing import Any

from .transcription import TranscriptResult, WordTiming

SPAN_TOLERANCE_SECONDS = 0.03
SEMANTIC_KINDS = {"possible_repetition", "possible_retake", "explicit_correction"}
SEMANTIC_PASS_DECISIONS = {"PROPOSED_CUT", "PROPOSED_TRIM"}
FILLER_PASS_STATUSES = {"isolated_hesitation"}
JOIN_PASS_STATUSES = {"join_context_only"}
ACOUSTIC_PASS_STATUSES = {"acoustic_context_only", "low_energy_boundary_context"}
_TOKEN_RE = re.compile(r"[^a-z0-9%€$£.,+-]+")


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _TOKEN_RE.sub("", asciiish).strip(".,")


def _normalised_phrase(text: str) -> list[str]:
    return [token for raw in text.split() if (token := _normalise(raw))]


def _words(transcript: TranscriptResult) -> list[WordTiming]:
    return sorted(
        [word for segment in transcript.segments for word in segment.words],
        key=lambda word: (word.start, word.end),
    )


def _text(words: list[WordTiming]) -> str:
    return " ".join(word.text for word in words).strip()


def _validate_removed_target(
    transcript: TranscriptResult,
    candidate: dict[str, Any],
    join: dict[str, Any],
) -> dict[str, Any]:
    target = join.get("target_span")
    if not isinstance(target, dict):
        return {
            "valid": False,
            "reason": "missing_target_span",
            "source": None,
            "text": None,
            "start": None,
            "end": None,
        }

    try:
        start = float(target["start"])
        end = float(target["end"])
    except (KeyError, TypeError, ValueError):
        return {
            "valid": False,
            "reason": "invalid_target_timestamps",
            "source": target.get("source"),
            "text": target.get("text"),
            "start": target.get("start"),
            "end": target.get("end"),
        }

    source = str(target.get("source") or "")
    target_text = str(target.get("text") or "")
    if start < 0.0 or end <= start:
        return {
            "valid": False,
            "reason": "invalid_target_interval",
            "source": source,
            "text": target_text,
            "start": start,
            "end": end,
        }

    if source == "candidate_temporal_gap":
        try:
            candidate_start = float(candidate["start"])
            candidate_end = float(candidate["end"])
        except (KeyError, TypeError, ValueError):
            candidate_start = -1.0
            candidate_end = -1.0
        timing_matches = (
            abs(candidate_start - start) <= SPAN_TOLERANCE_SECONDS
            and abs(candidate_end - end) <= SPAN_TOLERANCE_SECONDS
        )
        valid = (
            str(candidate.get("kind")) == "pause"
            and not target_text.strip()
            and timing_matches
        )
        return {
            "valid": valid,
            "reason": None if valid else "temporal_gap_target_mismatch",
            "source": source,
            "text": "",
            "start": start,
            "end": end,
            "transcript_text": "",
            "text_matches": not target_text.strip(),
            "timing_matches": timing_matches,
        }

    words = _words(transcript)
    try:
        word_start = int(target["start_index"])
        word_end = int(target["end_index_exclusive"])
    except (KeyError, TypeError, ValueError):
        return {
            "valid": False,
            "reason": "missing_target_word_indices",
            "source": source,
            "text": target_text,
            "start": start,
            "end": end,
        }

    if word_start < 0 or word_end <= word_start or word_end > len(words):
        return {
            "valid": False,
            "reason": "target_word_indices_out_of_bounds",
            "source": source,
            "text": target_text,
            "start": start,
            "end": end,
            "word_start_index": word_start,
            "word_end_index_exclusive": word_end,
        }

    selected = words[word_start:word_end]
    transcript_text = _text(selected)
    text_matches = _normalised_phrase(transcript_text) == _normalised_phrase(target_text)
    timing_matches = (
        abs(selected[0].start - start) <= SPAN_TOLERANCE_SECONDS
        and abs(selected[-1].end - end) <= SPAN_TOLERANCE_SECONDS
    )
    valid = text_matches and timing_matches
    return {
        "valid": valid,
        "reason": None if valid else "removed_text_target_mismatch",
        "source": source,
        "text": target_text,
        "start": start,
        "end": end,
        "word_start_index": word_start,
        "word_end_index_exclusive": word_end,
        "transcript_text": transcript_text,
        "text_matches": text_matches,
        "timing_matches": timing_matches,
    }


def _record(
    *,
    index: int,
    candidate: dict[str, Any],
    status: str,
    blockers: list[str],
    removed_text_validation: dict[str, Any],
    semantic_decision: dict[str, Any] | None,
    correction_scope: dict[str, Any] | None,
    filler_assessment: dict[str, Any] | None,
    join_assessment: dict[str, Any],
    acoustic_assessment: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "id": f"eligibility-assessment-{index:04d}",
        "candidate_id": candidate.get("id"),
        "candidate_kind": candidate.get("kind"),
        "status": status,
        "blockers": blockers,
        "future_promotion_candidate": status == "foundation_guards_pass",
        "removed_text_validation": removed_text_validation,
        "semantic_decision": (
            {
                "id": semantic_decision.get("id"),
                "decision": semantic_decision.get("decision"),
                "guard_status": semantic_decision.get("guard_status"),
            }
            if semantic_decision
            else None
        ),
        "correction_scope_status": correction_scope.get("status") if correction_scope else None,
        "filler_status": filler_assessment.get("status") if filler_assessment else None,
        "join_status": join_assessment.get("status"),
        "acoustic_status": acoustic_assessment.get("status") if acoustic_assessment else None,
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def build_eligibility_assessments(
    transcript: TranscriptResult,
    candidates: list[dict[str, Any]],
    *,
    semantic_decisions: list[dict[str, Any]],
    correction_scopes: list[dict[str, Any]],
    filler_assessments: list[dict[str, Any]],
    join_assessments: list[dict[str, Any]],
    acoustic_join_assessments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Combine upstream evidence without authorizing or executing any edit.

    Guard precedence is fail-safe and cumulative: a later clean signal can never
    rescue an earlier semantic/scope/filler/join blocker. `foundation_guards_pass`
    only means that the currently implemented foundation checks passed; it is not
    a cut authorization and remains `safe_for_cut=false`.
    """
    candidate_by_id = {str(item.get("id")): item for item in candidates if item.get("id")}
    semantic_by_candidate = {
        str(item.get("candidate_id")): item
        for item in semantic_decisions
        if item.get("candidate_id")
    }
    scope_by_candidate = {
        str(item.get("candidate_id")): item
        for item in correction_scopes
        if item.get("candidate_id")
    }
    filler_by_candidate = {
        str(item.get("candidate_id")): item
        for item in filler_assessments
        if item.get("candidate_id")
    }
    acoustic_by_join = {
        str(item.get("join_assessment_id")): item
        for item in acoustic_join_assessments
        if item.get("join_assessment_id")
    }

    results: list[dict[str, Any]] = []
    for join in join_assessments:
        candidate_id = str(join.get("candidate_id") or "")
        candidate = candidate_by_id.get(candidate_id)
        if candidate is None:
            continue

        kind = str(candidate.get("kind") or "")
        semantic = semantic_by_candidate.get(candidate_id)
        scope = scope_by_candidate.get(candidate_id)
        filler = filler_by_candidate.get(candidate_id)
        acoustic = acoustic_by_join.get(str(join.get("id") or ""))
        removed = _validate_removed_target(transcript, candidate, join)
        blockers: list[str] = []

        # An unbounded correction intentionally has no join target. Diagnose the
        # upstream scope blocker before treating that expected absence as target
        # corruption. This changes diagnostic precedence only, never permissiveness.
        if kind == "explicit_correction" and (scope is None or scope.get("status") != "bounded"):
            status = "blocked_correction_scope"
            blockers.append("correction_scope_not_bounded")
        elif not removed.get("valid"):
            status = "invalid_removed_text"
            blockers.append(str(removed.get("reason") or "invalid_removed_text"))
        elif kind == "possible_filler" and (
            filler is None or str(filler.get("status")) not in FILLER_PASS_STATUSES
        ):
            status = "blocked_filler_context"
            blockers.append("filler_context_not_isolated_hesitation")
        elif kind in SEMANTIC_KINDS and semantic is None:
            status = "missing_required_evidence"
            blockers.append("missing_semantic_decision")
        elif kind in SEMANTIC_KINDS and (
            str(semantic.get("decision")) not in SEMANTIC_PASS_DECISIONS
            or str(semantic.get("guard_status")) != "pass"
        ):
            status = "blocked_semantic_decision"
            blockers.append("semantic_decision_not_pass")
        elif str(join.get("status")) not in JOIN_PASS_STATUSES:
            status = "blocked_join_context"
            blockers.append("join_context_not_clean")
        elif acoustic is None:
            status = "missing_required_evidence"
            blockers.append("missing_acoustic_assessment")
        elif (
            str(acoustic.get("status")) not in ACOUSTIC_PASS_STATUSES
            or not bool(acoustic.get("measurement_available"))
        ):
            status = "blocked_acoustic_context"
            blockers.append("acoustic_context_not_clean_or_unmeasured")
        else:
            status = "foundation_guards_pass"

        results.append(
            _record(
                index=len(results) + 1,
                candidate=candidate,
                status=status,
                blockers=blockers,
                removed_text_validation=removed,
                semantic_decision=semantic,
                correction_scope=scope,
                filler_assessment=filler,
                join_assessment=join,
                acoustic_assessment=acoustic,
            )
        )

    return results
