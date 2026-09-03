from __future__ import annotations

from typing import Any

from .correction_scope import build_correction_scopes
from .semantic_candidates import build_semantic_candidates
from .transcription import TranscriptResult, TranscriptSegment, WordTiming


def materialise_scope_transcript(text: str, *, step: float = 0.32) -> TranscriptResult:
    """Create deterministic timings to isolate correction-scope logic from ASR."""
    words: list[WordTiming] = []
    cursor = 0.1
    for token in text.split():
        words.append(WordTiming(token, cursor, cursor + step * 0.72, 0.99))
        cursor += step
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=text,
                start=words[0].start if words else 0.0,
                end=words[-1].end if words else 0.0,
                words=tuple(words),
            ),
        ),
    )


def _assign_candidate_ids(candidates: list[dict[str, Any]]) -> None:
    counters: dict[str, int] = {}
    for candidate in candidates:
        kind = str(candidate["kind"])
        counters[kind] = counters.get(kind, 0) + 1
        candidate["id"] = f"{kind}-{counters[kind]:04d}"


def evaluate_correction_scope_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    metrics = {
        "cases": len(cases),
        "expected_candidate_cases": 0,
        "actual_scope_records": 0,
        "candidate_misses": 0,
        "candidate_false_positives": 0,
        "scope_count_mismatches": 0,
        "expected_bounded": 0,
        "bounded_exact": 0,
        "bounded_wrong": 0,
        "expected_ambiguous": 0,
        "ambiguous_correct": 0,
        "status_mismatches": 0,
        "strategy_mismatches": 0,
        "attempt_text_mismatches": 0,
        "unsafe_bounded": 0,
        "safety_violations": 0,
    }

    for case in cases:
        transcript = materialise_scope_transcript(str(case["text"]))
        candidates = build_semantic_candidates(transcript, mode="conservative")
        _assign_candidate_ids(candidates)
        scopes = build_correction_scopes(transcript, candidates)
        metrics["actual_scope_records"] += len(scopes)

        expect_candidate = bool(case.get("expect_correction_candidate"))
        expected_status = case.get("expected_status")
        expected_strategy = case.get("expected_strategy")
        expected_attempt_text = case.get("expected_attempt_text")

        if expect_candidate:
            metrics["expected_candidate_cases"] += 1
            if not scopes:
                metrics["candidate_misses"] += 1
        elif scopes:
            metrics["candidate_false_positives"] += 1

        if len(scopes) > 1 or (expect_candidate and len(scopes) != 1) or (not expect_candidate and scopes):
            metrics["scope_count_mismatches"] += 1

        scope = scopes[0] if len(scopes) == 1 else None
        actual_status = scope.get("status") if scope else None
        actual_strategy = scope.get("strategy") if scope else None
        actual_attempt_text = (
            ((scope.get("attempt_span") or {}).get("text")) if scope else None
        )

        if expected_status == "bounded":
            metrics["expected_bounded"] += 1
            if (
                actual_status == "bounded"
                and actual_strategy == expected_strategy
                and actual_attempt_text == expected_attempt_text
            ):
                metrics["bounded_exact"] += 1
            elif scope is not None:
                metrics["bounded_wrong"] += 1
        elif expected_status == "ambiguous":
            metrics["expected_ambiguous"] += 1
            if actual_status == "ambiguous":
                metrics["ambiguous_correct"] += 1
            elif actual_status == "bounded":
                metrics["unsafe_bounded"] += 1

        if actual_status != expected_status:
            metrics["status_mismatches"] += 1
        if actual_strategy != expected_strategy:
            metrics["strategy_mismatches"] += 1
        if actual_attempt_text != expected_attempt_text:
            metrics["attempt_text_mismatches"] += 1

        if scope and (
            scope.get("safe_for_cut")
            or scope.get("executable")
            or scope.get("auto_apply")
        ):
            metrics["safety_violations"] += 1

        details.append(
            {
                "id": case.get("id"),
                "source_type": case.get("source_type"),
                "expect_candidate": expect_candidate,
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_strategy": expected_strategy,
                "actual_strategy": actual_strategy,
                "expected_attempt_text": expected_attempt_text,
                "actual_attempt_text": actual_attempt_text,
                "scope_count": len(scopes),
                "safe_for_cut": bool(scope and scope.get("safe_for_cut")),
                "executable": bool(scope and scope.get("executable")),
                "auto_apply": bool(scope and scope.get("auto_apply")),
            }
        )

    expected_bounded = metrics["expected_bounded"]
    expected_scope = metrics["expected_bounded"] + metrics["expected_ambiguous"]
    metrics["bounded_exactness"] = (
        metrics["bounded_exact"] / expected_bounded if expected_bounded else 1.0
    )
    metrics["scope_status_accuracy"] = (
        (expected_scope - metrics["status_mismatches"]) / expected_scope
        if expected_scope
        else 1.0
    )
    return {"metrics": metrics, "cases": details}


def correction_scope_gate(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report["metrics"]
    checks = {
        "candidate_contract": metrics["candidate_misses"] == 0
        and metrics["candidate_false_positives"] == 0
        and metrics["scope_count_mismatches"] == 0,
        "bounded_exactness": metrics["bounded_exactness"] == 1.0,
        "scope_status": metrics["status_mismatches"] == 0
        and metrics["strategy_mismatches"] == 0
        and metrics["attempt_text_mismatches"] == 0,
        "no_unsafe_bounded": metrics["unsafe_bounded"] == 0,
        "non_executable": metrics["safety_violations"] == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}
