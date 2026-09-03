from __future__ import annotations

from collections import Counter
from typing import Any


def join_assessment_summary(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(item.get("status") or "unknown") for item in assessments)
    return {
        "count": len(assessments),
        "by_status": dict(sorted(statuses.items())),
        "target_resolved": sum(
            1 for item in assessments if bool((item.get("evidence") or {}).get("target_resolved"))
        ),
        "bilateral_context": sum(
            1 for item in assessments if bool((item.get("evidence") or {}).get("bilateral_context"))
        ),
        "safe_for_cut": sum(1 for item in assessments if item.get("safe_for_cut")),
        "executable": sum(1 for item in assessments if item.get("executable")),
        "auto_apply": sum(1 for item in assessments if item.get("auto_apply")),
    }


def attach_join_assessments(
    report: dict[str, Any], assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach join-boundary evidence without promoting it to an edit."""
    report["schema_version"] = max(6, int(report.get("schema_version") or 0))
    report["join_assessments"] = assessments
    report["summary"]["join_assessments"] = join_assessment_summary(assessments)
    report["safety"]["join_assessments_are_not_edits"] = True
    report["safety"]["join_assessments_executable"] = False
    report["safety"]["join_assessments_safe_for_cut"] = False
    report["safety"]["join_acoustic_validation_enabled"] = False
    report["safety"]["note"] = (
        "Candidates, correction scopes, filler assessments, join assessments y semantic decisions "
        "permanecen separados de edits. La foundation v1 de joins sólo acredita contexto "
        "timeline/léxico/segmental; la validación acústica del empalme aún no está habilitada."
    )
    return report
