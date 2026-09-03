from __future__ import annotations

from collections import Counter
from typing import Any

from .candidates import build_candidates
from .filler_context import build_filler_assessments
from .semantic_candidates import build_semantic_candidates
from .transcription import TranscriptResult, TranscriptSegment, WordTiming
from .vad import SpeechInterval


def materialise_filler_transcript(case: dict[str, Any], *, step: float = 0.32) -> TranscriptResult:
    """Create deterministic word timings to isolate contextual filler logic from ASR."""
    tokens = str(case["text"]).split()
    probabilities = case.get("probabilities") or [0.99] * len(tokens)
    starts = case.get("starts")
    if len(probabilities) != len(tokens):
        raise ValueError(f"Probability count mismatch for case {case.get('id')}")
    if starts is not None and len(starts) != len(tokens):
        raise ValueError(f"Start count mismatch for case {case.get('id')}")

    words: list[WordTiming] = []
    cursor = 0.1
    for index, token in enumerate(tokens):
        start = float(starts[index]) if starts is not None else cursor
        end = start + step * 0.72
        words.append(WordTiming(token, start, end, float(probabilities[index])))
        cursor = start + step

    return TranscriptResult(
        language=str(case.get("language") or "es"),
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=str(case["text"]),
                start=words[0].start if words else 0.0,
                end=words[-1].end if words else 0.0,
                words=tuple(words),
            ),
        ),
    )


def _all_candidates(transcript: TranscriptResult) -> list[dict[str, Any]]:
    words = [word for segment in transcript.segments for word in segment.words]
    duration = max(0.5, max((word.end for word in words), default=0.5))
    candidates = build_candidates(
        transcript,
        [SpeechInterval(0.0, duration)],
        duration=duration,
        mode="conservative",
    )
    semantic = build_semantic_candidates(transcript, mode="conservative")
    counters: dict[str, int] = {}
    for candidate in semantic:
        kind = str(candidate["kind"])
        counters[kind] = counters.get(kind, 0) + 1
        candidate["id"] = f"{kind}-{counters[kind]:04d}"
        candidate["auto_apply"] = False
        candidate["decision"] = "undecided"
        candidates.append(candidate)
    candidates.sort(key=lambda item: (float(item["start"]), float(item["end"]), item["kind"]))
    return candidates


def evaluate_filler_context_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {
        "cases": len(cases),
        "expected_records": 0,
        "actual_records": 0,
        "record_count_mismatches": 0,
        "status_mismatches": 0,
        "repair_link_mismatches": 0,
        "expected_protected_repair": 0,
        "protected_repair_correct": 0,
        "safety_violations": 0,
        "expected_status_counts": {},
        "actual_status_counts": {},
    }
    expected_counter: Counter[str] = Counter()
    actual_counter: Counter[str] = Counter()

    for case in cases:
        transcript = materialise_filler_transcript(case)
        candidates = _all_candidates(transcript)
        assessments = build_filler_assessments(transcript, candidates)
        expected_statuses = list(case.get("expected_statuses") or [])
        actual_statuses = [str(item.get("status")) for item in assessments]
        expect_repair_link = bool(case.get("expect_repair_link"))

        metrics["expected_records"] += len(expected_statuses)
        metrics["actual_records"] += len(assessments)
        expected_counter.update(expected_statuses)
        actual_counter.update(actual_statuses)

        if len(expected_statuses) != len(actual_statuses):
            metrics["record_count_mismatches"] += 1
        if expected_statuses != actual_statuses:
            metrics["status_mismatches"] += 1

        if "protected_repair_context" in expected_statuses:
            metrics["expected_protected_repair"] += expected_statuses.count("protected_repair_context")
            metrics["protected_repair_correct"] += sum(
                1 for status in actual_statuses if status == "protected_repair_context"
            )

        actual_has_repair_link = any(bool(item.get("repair_candidate_ids")) for item in assessments)
        if expect_repair_link != actual_has_repair_link:
            metrics["repair_link_mismatches"] += 1

        for item in assessments:
            if item.get("safe_for_cut") or item.get("executable") or item.get("auto_apply"):
                metrics["safety_violations"] += 1

        details.append(
            {
                "id": case.get("id"),
                "source_type": case.get("source_type"),
                "source_reference": case.get("source_reference"),
                "expected_statuses": expected_statuses,
                "actual_statuses": actual_statuses,
                "expected_repair_link": expect_repair_link,
                "actual_repair_link": actual_has_repair_link,
                "assessment_count": len(assessments),
                "safe_for_cut": any(bool(item.get("safe_for_cut")) for item in assessments),
                "executable": any(bool(item.get("executable")) for item in assessments),
                "auto_apply": any(bool(item.get("auto_apply")) for item in assessments),
            }
        )

    metrics["expected_status_counts"] = dict(sorted(expected_counter.items()))
    metrics["actual_status_counts"] = dict(sorted(actual_counter.items()))
    metrics["status_accuracy"] = (
        (metrics["cases"] - metrics["status_mismatches"]) / metrics["cases"]
        if metrics["cases"]
        else 1.0
    )
    expected_protected = metrics["expected_protected_repair"]
    metrics["repair_protection_recall"] = (
        metrics["protected_repair_correct"] / expected_protected if expected_protected else 1.0
    )
    return {"metrics": metrics, "cases": details}


def filler_context_gate(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report["metrics"]
    checks = {
        "record_contract": metrics["record_count_mismatches"] == 0,
        "status_exactness": metrics["status_mismatches"] == 0
        and metrics["status_accuracy"] == 1.0,
        "repair_protection": metrics["repair_link_mismatches"] == 0
        and metrics["repair_protection_recall"] == 1.0,
        "non_executable": metrics["safety_violations"] == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}
