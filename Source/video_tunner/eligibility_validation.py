from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .eligibility import build_eligibility_assessments
from .transcription import TranscriptResult, TranscriptSegment, WordTiming

REQUIRED_STATUSES = {
    "foundation_guards_pass",
    "blocked_acoustic_context",
    "blocked_filler_context",
    "blocked_semantic_decision",
    "blocked_join_context",
    "blocked_correction_scope",
    "invalid_removed_text",
    "missing_required_evidence",
}


def _transcript(payload: dict[str, Any]) -> TranscriptResult:
    words = tuple(
        WordTiming(
            str(item["text"]),
            float(item["start"]),
            float(item["end"]),
            None,
        )
        for item in payload["transcript_words"]
    )
    return TranscriptResult(
        language="en",
        language_probability=0.99,
        model="eligibility-fixture",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=" ".join(word.text for word in words),
                start=words[0].start,
                end=words[-1].end,
                words=words,
            ),
        ),
    )


def evaluate_eligibility_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    transcript = _transcript(payload)

    status_mismatches: list[dict[str, Any]] = []
    safety_violations: list[str] = []
    removed_text_failures: list[str] = []
    statuses_seen: set[str] = set()
    future_promotion_candidates = 0

    for case in payload["cases"]:
        candidate = case["candidate"]
        semantic = [case["semantic"]] if case.get("semantic") else []
        scopes = [case["scope"]] if case.get("scope") else []
        fillers = [case["filler"]] if case.get("filler") else []
        joins = [case["join"]]
        acoustics = [case["acoustic"]] if case.get("acoustic") else []
        assessments = build_eligibility_assessments(
            transcript,
            [candidate],
            semantic_decisions=semantic,
            correction_scopes=scopes,
            filler_assessments=fillers,
            join_assessments=joins,
            acoustic_join_assessments=acoustics,
        )
        if len(assessments) != 1:
            status_mismatches.append(
                {
                    "case_id": case["id"],
                    "expected": case["expected_status"],
                    "actual": f"record_count={len(assessments)}",
                }
            )
            continue

        item = assessments[0]
        status = str(item.get("status"))
        statuses_seen.add(status)
        if status != str(case["expected_status"]):
            status_mismatches.append(
                {
                    "case_id": case["id"],
                    "expected": case["expected_status"],
                    "actual": status,
                }
            )

        removed = item.get("removed_text_validation") or {}
        if status != "invalid_removed_text" and not bool(removed.get("valid")):
            removed_text_failures.append(str(case["id"]))

        if item.get("safe_for_cut") or item.get("executable") or item.get("auto_apply"):
            safety_violations.append(str(case["id"]))
        if item.get("future_promotion_candidate"):
            future_promotion_candidates += 1
            if status != "foundation_guards_pass":
                safety_violations.append(str(case["id"]) + ":promotion_flag_without_pass")

    missing_statuses = sorted(REQUIRED_STATUSES - statuses_seen)
    return {
        "cases": len(payload["cases"]),
        "status_mismatches": status_mismatches,
        "status_mismatch_count": len(status_mismatches),
        "removed_text_failures": removed_text_failures,
        "removed_text_failure_count": len(removed_text_failures),
        "safety_violations": safety_violations,
        "safety_violation_count": len(safety_violations),
        "statuses_seen": sorted(statuses_seen),
        "missing_required_statuses": missing_statuses,
        "future_promotion_candidates": future_promotion_candidates,
        "safe_for_cut": 0,
        "executable": 0,
        "auto_apply": 0,
    }


def eligibility_gate(metrics: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "enough_cases": int(metrics["cases"]) >= 10,
        "all_statuses_exercised": not metrics["missing_required_statuses"],
        "status_contract_exact": int(metrics["status_mismatch_count"]) == 0,
        "removed_text_contract_exact": int(metrics["removed_text_failure_count"]) == 0,
        "safety_violations_zero": int(metrics["safety_violation_count"]) == 0,
        "positive_paths_exist": int(metrics["future_promotion_candidates"]) >= 3,
        "non_executable": int(metrics["safe_for_cut"]) == 0
        and int(metrics["executable"]) == 0
        and int(metrics["auto_apply"]) == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}
