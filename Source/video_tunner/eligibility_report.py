from __future__ import annotations

from collections import Counter
from typing import Any


def eligibility_summary(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(item.get("status") or "unknown") for item in assessments)
    return {
        "count": len(assessments),
        "by_status": dict(sorted(statuses.items())),
        "future_promotion_candidates": sum(
            1 for item in assessments if bool(item.get("future_promotion_candidate"))
        ),
        "removed_text_valid": sum(
            1
            for item in assessments
            if bool((item.get("removed_text_validation") or {}).get("valid"))
        ),
        "safe_for_cut": sum(1 for item in assessments if item.get("safe_for_cut")),
        "executable": sum(1 for item in assessments if item.get("executable")),
        "auto_apply": sum(1 for item in assessments if item.get("auto_apply")),
    }


def attach_eligibility_assessments(
    report: dict[str, Any], assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach combined foundation guard results without promoting edits."""
    report["schema_version"] = max(8, int(report.get("schema_version") or 0))
    report["eligibility_assessments"] = assessments
    report["summary"]["eligibility_assessments"] = eligibility_summary(assessments)
    report["safety"]["eligibility_assessments_are_not_edits"] = True
    report["safety"]["eligibility_assessments_executable"] = False
    report["safety"]["eligibility_assessments_safe_for_cut"] = False
    report["safety"]["future_promotion_candidates_are_not_approved_edits"] = True
    report["safety"]["combined_eligibility_enabled"] = True
    report["safety"]["combined_eligibility_is_not_edit_plan_promotion"] = True
    report["safety"]["note"] = (
        "Eligibility assessments combine semantic, scope, filler, join and acoustic guards. "
        "Even foundation_guards_pass only marks a future-promotion candidate; no record is "
        "safe-for-cut, executable or auto-applied and no Edit Plan promotion occurs."
    )
    return report
