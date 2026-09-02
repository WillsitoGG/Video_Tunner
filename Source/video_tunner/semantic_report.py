from __future__ import annotations

from typing import Any

from .semantic_decisions import semantic_decision_summary


def attach_semantic_decisions(
    report: dict[str, Any], decisions: list[dict[str, Any]]
) -> dict[str, Any]:
    """Upgrade an analysis report with a separate, non-executable decision layer."""
    report["schema_version"] = 3
    report["semantic_decisions"] = decisions
    report["summary"]["semantic_decisions"] = semantic_decision_summary(decisions)
    report["safety"]["semantic_protection_enabled"] = True
    report["safety"]["semantic_decisions_are_not_edits"] = True
    report["safety"]["semantic_decisions_executable"] = False
    report["safety"]["note"] = (
        "Candidates y semantic decisions permanecen separados de edits; ninguna propuesta es ejecutable."
    )
    return report
