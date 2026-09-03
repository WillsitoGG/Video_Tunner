from __future__ import annotations

from collections import Counter
from typing import Any


def filler_assessment_summary(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(item.get("status") or "unknown") for item in assessments)
    return {
        "count": len(assessments),
        "by_status": dict(sorted(statuses.items())),
        "protected_repair_context": statuses.get("protected_repair_context", 0),
        "safe_for_cut": sum(1 for item in assessments if item.get("safe_for_cut")),
        "executable": sum(1 for item in assessments if item.get("executable")),
        "auto_apply": sum(1 for item in assessments if item.get("auto_apply")),
    }


def attach_filler_assessments(
    report: dict[str, Any], assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach contextual filler evidence as a separate non-edit analysis layer."""
    report["schema_version"] = max(5, int(report.get("schema_version") or 0))
    report["filler_assessments"] = assessments
    report["summary"]["filler_assessments"] = filler_assessment_summary(assessments)
    report["safety"]["filler_assessments_are_not_edits"] = True
    report["safety"]["filler_assessments_executable"] = False
    report["safety"]["filler_assessments_safe_for_cut"] = False
    report["safety"]["note"] = (
        "Candidates, correction scopes, filler assessments y semantic decisions permanecen "
        "separados de edits; ningún filler assessment autoriza un corte."
    )
    return report
