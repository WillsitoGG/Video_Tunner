from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any, Iterable

from .semantic_candidates import build_semantic_candidates
from .semantic_decisions import build_semantic_decisions
from .transcription import TranscriptResult, TranscriptSegment, WordTiming

_TOKEN_RE = re.compile(r"[^a-z0-9%€$£.,+-]+")


def _normalise(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(
        token
        for raw in asciiish.split()
        if (token := _TOKEN_RE.sub("", raw).strip(".,"))
    )


def transcript_from_case(case: dict[str, Any]) -> TranscriptResult:
    """Materialise a lightweight, deterministic spoken-style transcript fixture.

    The corpus validates the semantic layer independently from ASR quality. A later
    audio-backed corpus may feed the same evaluator with real Whisper transcripts.
    """
    text = str(case["text"]).strip()
    tokens = text.split()
    step = float(case.get("step_seconds", 0.32))
    duration = float(case.get("word_duration_seconds", step * 0.72))
    cursor = float(case.get("start_seconds", 0.1))
    pause_after = {int(k): float(v) for k, v in (case.get("pause_after") or {}).items()}

    words: list[WordTiming] = []
    for index, token in enumerate(tokens):
        words.append(WordTiming(token, cursor, cursor + duration, 0.99))
        cursor += step + pause_after.get(index, 0.0)

    return TranscriptResult(
        language=str(case.get("language", "es")),
        language_probability=0.99,
        model="semantic-corpus-v1",
        device="fixture",
        compute_type="n/a",
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


def _event_key(kind: str, removed_text: str) -> tuple[str, str]:
    return kind, _normalise(removed_text)


def evaluate_semantic_cases(
    cases: Iterable[dict[str, Any]],
    *,
    mode: str = "conservative",
) -> dict[str, Any]:
    """Evaluate candidate detection and decision safety on labelled cases.

    Candidate precision/recall and proposal safety are intentionally separated:
    a review-only false positive is noise, while an unsafe PROPOSED_CUT is a safety
    failure. Nothing evaluated here can become executable.
    """
    total_expected = 0
    total_actual = 0
    true_positive = 0
    false_positive = 0
    false_negative = 0
    decision_mismatches = 0
    unsafe_proposals = 0
    missing_safe_proposals = 0
    executable_decisions = 0
    auto_apply_decisions = 0
    case_reports: list[dict[str, Any]] = []

    for case in cases:
        transcript = transcript_from_case(case)
        candidates = build_semantic_candidates(transcript, mode=mode)
        _assign_candidate_ids(candidates)
        decisions = build_semantic_decisions(transcript, candidates)
        decisions_by_candidate = {item["candidate_id"]: item for item in decisions}

        expected_events = list(case.get("expected_events") or [])
        expected_by_key = {
            _event_key(str(item["kind"]), str(item["removed_text"])): item
            for item in expected_events
        }
        actual_by_key = {
            _event_key(str(item["kind"]), str((item.get("evidence") or {}).get("removed_text") or "")): item
            for item in candidates
        }

        expected_keys = set(expected_by_key)
        actual_keys = set(actual_by_key)
        matched = expected_keys & actual_keys
        missing = expected_keys - actual_keys
        unexpected = actual_keys - expected_keys

        total_expected += len(expected_keys)
        total_actual += len(actual_keys)
        true_positive += len(matched)
        false_negative += len(missing)
        false_positive += len(unexpected)

        mismatches: list[dict[str, Any]] = []
        unsafe: list[dict[str, Any]] = []
        missing_proposals: list[dict[str, Any]] = []

        for key in matched:
            expected = expected_by_key[key]
            candidate = actual_by_key[key]
            decision = decisions_by_candidate.get(candidate["id"])
            expected_decision = expected.get("decision")
            if expected_decision and (decision or {}).get("decision") != expected_decision:
                decision_mismatches += 1
                mismatches.append(
                    {
                        "event": {"kind": key[0], "removed_text": key[1]},
                        "expected": expected_decision,
                        "actual": (decision or {}).get("decision"),
                    }
                )
            if expected_decision == "PROPOSED_CUT" and (decision or {}).get("decision") != "PROPOSED_CUT":
                missing_safe_proposals += 1
                missing_proposals.append(
                    {"kind": key[0], "removed_text": key[1], "actual": (decision or {}).get("decision")}
                )

        for candidate in candidates:
            decision = decisions_by_candidate.get(candidate["id"])
            if not decision:
                continue
            executable_decisions += int(bool(decision.get("executable")))
            auto_apply_decisions += int(bool(decision.get("auto_apply")))
            if decision.get("decision") != "PROPOSED_CUT":
                continue
            key = _event_key(
                str(candidate["kind"]),
                str((candidate.get("evidence") or {}).get("removed_text") or ""),
            )
            expected = expected_by_key.get(key)
            if expected is None or expected.get("decision") != "PROPOSED_CUT":
                unsafe_proposals += 1
                unsafe.append(
                    {
                        "candidate_id": candidate["id"],
                        "kind": candidate["kind"],
                        "removed_text": (candidate.get("evidence") or {}).get("removed_text"),
                    }
                )

        case_reports.append(
            {
                "id": case["id"],
                "description": case.get("description"),
                "expected_events": expected_events,
                "actual_candidates": [
                    {
                        "id": item["id"],
                        "kind": item["kind"],
                        "removed_text": (item.get("evidence") or {}).get("removed_text"),
                        "decision": (decisions_by_candidate.get(item["id"]) or {}).get("decision"),
                        "guard_status": (decisions_by_candidate.get(item["id"]) or {}).get("guard_status"),
                    }
                    for item in candidates
                ],
                "false_negatives": [
                    {"kind": kind, "removed_text": text} for kind, text in sorted(missing)
                ],
                "false_positives": [
                    {"kind": kind, "removed_text": text} for kind, text in sorted(unexpected)
                ],
                "decision_mismatches": mismatches,
                "unsafe_proposals": unsafe,
                "missing_safe_proposals": missing_proposals,
            }
        )

    precision = true_positive / total_actual if total_actual else 1.0
    recall = true_positive / total_expected if total_expected else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "schema_version": 1,
        "mode": mode,
        "summary": {
            "cases": len(case_reports),
            "expected_events": total_expected,
            "actual_candidates": total_actual,
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "candidate_precision": round(precision, 4),
            "candidate_recall": round(recall, 4),
            "candidate_f1": round(f1, 4),
            "decision_mismatches": decision_mismatches,
            "unsafe_proposals": unsafe_proposals,
            "missing_safe_proposals": missing_safe_proposals,
            "executable_decisions": executable_decisions,
            "auto_apply_decisions": auto_apply_decisions,
        },
        "cases": case_reports,
    }


def validation_gate(
    report: dict[str, Any],
    *,
    minimum_precision: float = 0.80,
    minimum_recall: float = 0.90,
) -> dict[str, Any]:
    """Return an explicit gate result without promoting any semantic edit."""
    summary = report["summary"]
    checks = {
        "candidate_precision": float(summary["candidate_precision"]) >= minimum_precision,
        "candidate_recall": float(summary["candidate_recall"]) >= minimum_recall,
        "decision_contract": int(summary["decision_mismatches"]) == 0,
        "proposal_safety": int(summary["unsafe_proposals"]) == 0,
        "expected_safe_proposals": int(summary["missing_safe_proposals"]) == 0,
        "non_executable": int(summary["executable_decisions"]) == 0,
        "no_auto_apply": int(summary["auto_apply_decisions"]) == 0,
    }
    return {
        "passed": all(checks.values()),
        "thresholds": {
            "minimum_precision": minimum_precision,
            "minimum_recall": minimum_recall,
        },
        "checks": checks,
        "failures": [name for name, passed in checks.items() if not passed],
    }
