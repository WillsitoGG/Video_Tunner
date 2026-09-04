from __future__ import annotations

from collections import Counter
from typing import Any


def promotion_summary(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(item.get("status") or "unknown") for item in assessments)
    return {
        "count": len(assessments),
        "by_status": dict(sorted(statuses.items())),
        "promotion_review_candidates": sum(
            1 for item in assessments if bool(item.get("promotion_review_candidate"))
        ),
        "approved": sum(1 for item in assessments if item.get("approved")),
        "edits": sum(1 for item in assessments if item.get("edit") is not None),
        "safe_for_cut": sum(1 for item in assessments if item.get("safe_for_cut")),
        "executable": sum(1 for item in assessments if item.get("executable")),
        "auto_apply": sum(1 for item in assessments if item.get("auto_apply")),
    }


def attach_promotion_assessments(
    report: dict[str, Any], assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach Phase 2E.1 review-only promotion assessments; never create edits."""
    report["schema_version"] = max(9, int(report.get("schema_version") or 0))
    report["promotion_assessments"] = assessments
    report["summary"]["promotion_assessments"] = promotion_summary(assessments)
    report["safety"]["promotion_assessments_are_not_edits"] = True
    report["safety"]["promotion_review_requires_explicit_approval"] = True
    report["safety"]["promotion_assessments_approved"] = False
    report["safety"]["edit_plan_promotion_enabled"] = False
    report["safety"]["promotion_assessments_executable"] = False
    report["safety"]["promotion_assessments_safe_for_cut"] = False
    report["safety"]["note"] = (
        "Phase 2E.1 can identify evidence-backed records for explicit promotion review, "
        "but every assessment remains unapproved and contains edit=null. No Edit Plan "
        "promotion, cut execution or auto-apply is enabled."
    )
    return report
