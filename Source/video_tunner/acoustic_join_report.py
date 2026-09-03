from __future__ import annotations

from collections import Counter
from typing import Any

RISK_STATUSES = {
    "level_discontinuity_risk",
    "waveform_discontinuity_risk",
    "combined_discontinuity_risk",
    "insufficient_audio_context",
    "blocked_by_context",
}


def acoustic_join_summary(assessments: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(item.get("status") or "unknown") for item in assessments)
    return {
        "count": len(assessments),
        "by_status": dict(sorted(statuses.items())),
        "measurement_available": sum(
            1 for item in assessments if bool(item.get("measurement_available"))
        ),
        "risk_or_blocked": sum(
            1 for item in assessments if str(item.get("status")) in RISK_STATUSES
        ),
        "safe_for_cut": sum(1 for item in assessments if item.get("safe_for_cut")),
        "executable": sum(1 for item in assessments if item.get("executable")),
        "auto_apply": sum(1 for item in assessments if item.get("auto_apply")),
    }


def attach_acoustic_join_assessments(
    report: dict[str, Any], assessments: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach waveform evidence while keeping every join non-executable."""
    report["schema_version"] = max(7, int(report.get("schema_version") or 0))
    report["acoustic_join_assessments"] = assessments
    report["summary"]["acoustic_join_assessments"] = acoustic_join_summary(assessments)
    report["safety"]["acoustic_join_assessments_are_not_edits"] = True
    report["safety"]["acoustic_join_assessments_executable"] = False
    report["safety"]["acoustic_join_assessments_safe_for_cut"] = False
    report["safety"]["join_acoustic_validation_enabled"] = True
    report["safety"]["join_acoustic_validation_is_not_cut_authorization"] = True
    report["safety"]["note"] = (
        "Candidates, correction scopes, filler assessments, join assessments, acoustic join "
        "assessments y semantic decisions permanecen separados de edits. La capa acústica "
        "mide el master real, pero ningún resultado autoriza por sí solo un corte."
    )
    return report
