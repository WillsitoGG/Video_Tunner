from __future__ import annotations

from collections import Counter
from typing import Any


def correction_scope_summary(scopes: list[dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(str(scope.get("status") or "unknown") for scope in scopes)
    strategies = Counter(str(scope.get("strategy") or "unknown") for scope in scopes)
    return {
        "count": len(scopes),
        "by_status": dict(sorted(statuses.items())),
        "by_strategy": dict(sorted(strategies.items())),
        "safe_for_cut": sum(1 for scope in scopes if scope.get("safe_for_cut")),
        "executable": sum(1 for scope in scopes if scope.get("executable")),
        "auto_apply": sum(1 for scope in scopes if scope.get("auto_apply")),
    }


def attach_correction_scopes(
    report: dict[str, Any], scopes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Attach correction-scope evidence as a separate non-edit analysis layer."""
    report["schema_version"] = max(4, int(report.get("schema_version") or 0))
    report["correction_scopes"] = scopes
    report["summary"]["correction_scopes"] = correction_scope_summary(scopes)
    report["safety"]["correction_scopes_are_not_edits"] = True
    report["safety"]["correction_scopes_executable"] = False
    report["safety"]["correction_scopes_safe_for_cut"] = False
    report["safety"]["note"] = (
        "Candidates, correction scopes y semantic decisions permanecen separados de edits; "
        "ningún correction scope autoriza un corte."
    )
    return report
