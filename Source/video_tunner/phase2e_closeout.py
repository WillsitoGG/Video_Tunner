from __future__ import annotations

from typing import Any

from .human_render_review import validate_human_render_review

PHASE2E_CLOSEOUT_SCHEMA_VERSION = 1
PHASE2E_CLOSEOUT_RECORD_TYPE = "phase2e_closeout_decision"
REQUIRED_CASES = 3
REQUIRED_SOURCES = 2
REQUIRED_TECHNICAL_PASS_FRACTION = 1.0
REQUIRED_HUMAN_PASS_FRACTION = 1.0
MAXIMUM_SAFETY_VIOLATIONS = 0


def _validate_locked_policy(manifest: dict[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(manifest, dict):
        return False, "manifest_not_object"
    if manifest.get("record_type") != "phase2e_human_render_review_bundle":
        return False, "invalid_manifest_record_type"
    if not manifest.get("selection_locked_before_listening"):
        return False, "selection_not_locked_before_listening"
    policy = manifest.get("closeout_policy")
    if not isinstance(policy, dict):
        return False, "missing_closeout_policy"
    expected = {
        "minimum_rendered_human_cases": REQUIRED_CASES,
        "minimum_distinct_audio_sources": REQUIRED_SOURCES,
        "required_technical_pass_fraction": REQUIRED_TECHNICAL_PASS_FRACTION,
        "required_human_perceptual_pass_fraction": REQUIRED_HUMAN_PASS_FRACTION,
        "maximum_safety_violations": MAXIMUM_SAFETY_VIOLATIONS,
        "decision_if_all_pass": "CLOSE_OUT_READY",
        "decision_if_any_fail": "INSUFFICIENT_JOIN_QUALITY",
    }
    for key, value in expected.items():
        if policy.get(key) != value:
            return False, f"closeout_policy_changed:{key}"
    return True, None


def build_phase2e_closeout_decision(
    manifest: dict[str, Any],
    technical_reports: dict[str, dict[str, Any]],
    human_reviews: dict[str, dict[str, Any]],
    *,
    technical_report_sha256: dict[str, str],
) -> dict[str, Any]:
    """Aggregate locked Phase 2E.5 evidence without relaxing the close-out bar.

    One human perceptual failure is enough to keep Phase 2E open. Invalid/stale
    evidence is distinguished from genuine join-quality failure.
    """
    base = {
        "schema_version": PHASE2E_CLOSEOUT_SCHEMA_VERSION,
        "record_type": PHASE2E_CLOSEOUT_RECORD_TYPE,
        "phase2e_closeout_ready": False,
        "auto_apply": False,
    }
    policy_valid, policy_reason = _validate_locked_policy(manifest)
    if not policy_valid:
        return base | {
            "status": "INVALID_EVIDENCE",
            "reason": policy_reason,
            "cases": [],
        }

    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != REQUIRED_CASES:
        return base | {
            "status": "INVALID_EVIDENCE",
            "reason": "case_count_mismatch",
            "cases": [],
        }
    source_ids = {str(item.get("audio_source_id") or "") for item in cases}
    if "" in source_ids or len(source_ids) < REQUIRED_SOURCES:
        return base | {
            "status": "INVALID_EVIDENCE",
            "reason": "distinct_source_count_below_locked_minimum",
            "cases": [],
        }
    if manifest.get("pre_human_gate") != "PASS":
        return base | {
            "status": "INVALID_EVIDENCE",
            "reason": "pre_human_gate_not_pass",
            "cases": [],
        }

    case_results: list[dict[str, Any]] = []
    invalid_count = 0
    human_fail_count = 0
    for case in cases:
        case_id = str(case.get("id") or "")
        report = technical_reports.get(case_id)
        review = human_reviews.get(case_id)
        report_sha = technical_report_sha256.get(case_id)
        if not case_id or not isinstance(report, dict) or not isinstance(review, dict) or not report_sha:
            invalid_count += 1
            case_results.append(
                {
                    "id": case_id,
                    "status": "invalid_or_missing_case_evidence",
                    "human_perceptual_pass": False,
                }
            )
            continue
        validation = validate_human_render_review(
            report,
            review,
            technical_report_sha256=report_sha,
        )
        valid = bool(validation.get("valid"))
        human_pass = bool(validation.get("human_perceptual_pass")) if valid else False
        if not valid:
            invalid_count += 1
        elif not human_pass:
            human_fail_count += 1
        case_results.append(
            {
                "id": case_id,
                "audio_source_id": case.get("audio_source_id"),
                "status": validation.get("status"),
                "valid": valid,
                "human_perceptual_pass": human_pass,
                "reviewed_join_count": int(validation.get("reviewed_join_count") or 0),
            }
        )

    valid_count = sum(bool(item.get("valid")) for item in case_results)
    human_pass_count = sum(bool(item.get("human_perceptual_pass")) for item in case_results)
    if invalid_count:
        status = "INVALID_EVIDENCE"
        reason = "one_or_more_reviews_invalid_or_stale"
        ready = False
    elif human_fail_count:
        status = "INSUFFICIENT_JOIN_QUALITY"
        reason = "one_or_more_human_perceptual_fails"
        ready = False
    elif valid_count == REQUIRED_CASES and human_pass_count == REQUIRED_CASES:
        status = "CLOSE_OUT_READY"
        reason = None
        ready = True
    else:
        status = "INVALID_EVIDENCE"
        reason = "locked_closeout_threshold_not_met"
        ready = False

    return base | {
        "status": status,
        "reason": reason,
        "phase2e_closeout_ready": ready,
        "summary": {
            "required_cases": REQUIRED_CASES,
            "evaluated_cases": len(case_results),
            "required_sources": REQUIRED_SOURCES,
            "distinct_sources": len(source_ids),
            "valid_review_count": valid_count,
            "human_perceptual_pass_count": human_pass_count,
            "human_perceptual_fail_count": human_fail_count,
            "invalid_or_stale_review_count": invalid_count,
        },
        "cases": case_results,
    }
