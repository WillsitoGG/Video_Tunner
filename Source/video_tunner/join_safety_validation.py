from __future__ import annotations

from collections import Counter
from typing import Any

from .join_safety import build_join_assessments
from .transcription import TranscriptResult, TranscriptSegment, WordTiming


def _span(words: list[WordTiming], start: int, end: int) -> dict[str, Any]:
    selected = words[start:end]
    return {
        "word_start_index": start,
        "word_end_index_exclusive": end,
        "start": selected[0].start,
        "end": selected[-1].end,
        "text": " ".join(word.text for word in selected),
    }


def materialise_join_case(
    case: dict[str, Any], *, step: float = 0.32, segment_gap: float = 0.48
) -> tuple[TranscriptResult, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Materialise deterministic join evidence from a labelled case."""
    segments: list[TranscriptSegment] = []
    words: list[WordTiming] = []
    cursor = 0.1
    for raw_segment in case["segments"]:
        segment_words: list[WordTiming] = []
        for token in raw_segment:
            word = WordTiming(str(token), cursor, cursor + step * 0.68, 0.99)
            segment_words.append(word)
            words.append(word)
            cursor += step
        segments.append(
            TranscriptSegment(
                text=" ".join(str(token) for token in raw_segment),
                start=segment_words[0].start,
                end=segment_words[-1].end,
                words=tuple(segment_words),
            )
        )
        cursor += segment_gap

    transcript = TranscriptResult(
        language=str(case.get("language") or "es"),
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=tuple(segments),
    )

    spec = case["candidate"]
    kind = str(spec["kind"])
    candidate_id = f"{kind}-0001"
    if kind == "pause":
        left, right = (int(index) for index in spec["between"])
        candidate = {
            "id": candidate_id,
            "kind": kind,
            "start": words[left].end,
            "end": words[right].start,
            "evidence": {},
            "auto_apply": False,
        }
    else:
        start, end = (int(index) for index in spec["span"])
        selected = words[start:end]
        if kind == "possible_filler":
            candidate = {
                "id": candidate_id,
                "kind": kind,
                "start": selected[0].start,
                "end": selected[-1].end,
                "evidence": {
                    "token": selected[0].text,
                    "transcription_probability": selected[0].probability,
                },
                "auto_apply": False,
            }
        else:
            removed_text = str(
                spec.get("removed_text_override")
                or " ".join(word.text for word in selected)
            )
            candidate = {
                "id": candidate_id,
                "kind": kind,
                "start": selected[0].start,
                "end": selected[-1].end,
                "evidence": {
                    "word_start_index": start,
                    "word_end_index_exclusive": end,
                    "removed_text": removed_text,
                },
                "auto_apply": False,
            }

    correction_scopes: list[dict[str, Any]] = []
    scope_spec = case.get("correction_scope")
    if scope_spec is not None:
        marker_start, marker_end = (int(index) for index in scope_spec["marker"])
        scope = {
            "id": "correction-scope-0001",
            "candidate_id": candidate_id,
            "candidate_kind": "explicit_correction",
            "status": scope_spec["status"],
            "marker_span": _span(words, marker_start, marker_end),
            "safe_for_cut": False,
            "executable": False,
            "auto_apply": False,
        }
        if scope_spec["status"] == "bounded":
            attempt_start, attempt_end = (int(index) for index in scope_spec["attempt"])
            scope["attempt_span"] = _span(words, attempt_start, attempt_end)
        else:
            scope["attempt_span"] = None
        correction_scopes.append(scope)

    filler_assessments: list[dict[str, Any]] = []
    filler_status = case.get("filler_assessment_status")
    if filler_status is not None:
        filler_assessments.append(
            {
                "id": "filler-assessment-0001",
                "candidate_id": candidate_id,
                "candidate_kind": "possible_filler",
                "status": filler_status,
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        )

    return transcript, [candidate], correction_scopes, filler_assessments


def evaluate_join_safety_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    expected_counter: Counter[str] = Counter()
    actual_counter: Counter[str] = Counter()
    metrics: dict[str, Any] = {
        "cases": len(cases),
        "status_mismatches": 0,
        "target_source_mismatches": 0,
        "bilateral_mismatches": 0,
        "safety_violations": 0,
        "expected_status_counts": {},
        "actual_status_counts": {},
    }

    for case in cases:
        transcript, candidates, scopes, fillers = materialise_join_case(case)
        assessments = build_join_assessments(
            transcript,
            candidates,
            correction_scopes=scopes,
            filler_assessments=fillers,
        )
        if len(assessments) != 1:
            raise AssertionError(f"Expected exactly one join assessment for {case.get('id')}")
        assessment = assessments[0]
        expected_status = str(case["expected_status"])
        actual_status = str(assessment["status"])
        expected_source = case.get("expected_target_source")
        actual_source = (
            None if assessment.get("target_span") is None else assessment["target_span"].get("source")
        )
        expected_bilateral = bool(case.get("expected_bilateral"))
        actual_bilateral = bool((assessment.get("evidence") or {}).get("bilateral_context"))

        expected_counter[expected_status] += 1
        actual_counter[actual_status] += 1
        if expected_status != actual_status:
            metrics["status_mismatches"] += 1
        if expected_source != actual_source:
            metrics["target_source_mismatches"] += 1
        if expected_bilateral != actual_bilateral:
            metrics["bilateral_mismatches"] += 1
        if assessment.get("safe_for_cut") or assessment.get("executable") or assessment.get("auto_apply"):
            metrics["safety_violations"] += 1

        details.append(
            {
                "id": case.get("id"),
                "source_type": case.get("source_type"),
                "source_reference": case.get("source_reference"),
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_target_source": expected_source,
                "actual_target_source": actual_source,
                "expected_bilateral": expected_bilateral,
                "actual_bilateral": actual_bilateral,
                "safe_for_cut": assessment.get("safe_for_cut"),
                "executable": assessment.get("executable"),
                "auto_apply": assessment.get("auto_apply"),
            }
        )

    metrics["expected_status_counts"] = dict(sorted(expected_counter.items()))
    metrics["actual_status_counts"] = dict(sorted(actual_counter.items()))
    metrics["status_accuracy"] = (
        (metrics["cases"] - metrics["status_mismatches"]) / metrics["cases"]
        if metrics["cases"]
        else 1.0
    )
    return {"metrics": metrics, "cases": details}


def join_safety_gate(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report["metrics"]
    checks = {
        "status_exactness": metrics["status_mismatches"] == 0
        and metrics["status_accuracy"] == 1.0,
        "target_resolution_contract": metrics["target_source_mismatches"] == 0,
        "bilateral_context_contract": metrics["bilateral_mismatches"] == 0,
        "non_executable": metrics["safety_violations"] == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}
