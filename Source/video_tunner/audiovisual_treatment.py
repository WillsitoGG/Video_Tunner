from __future__ import annotations

from typing import Any

from .audiovisual_quality import AUDIOVISUAL_QUALITY_RECORD_TYPE, AUDIOVISUAL_QUALITY_SCHEMA_VERSION

AUDIOVISUAL_TREATMENT_SCHEMA_VERSION = 1
AUDIOVISUAL_TREATMENT_RECORD_TYPE = "audiovisual_treatment_decision"


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _validate_quality_audit(audit: dict[str, Any]) -> None:
    if not isinstance(audit, dict):
        raise ValueError("Audiovisual quality audit debe ser un objeto JSON.")
    if audit.get("schema_version") != AUDIOVISUAL_QUALITY_SCHEMA_VERSION:
        raise ValueError("Audiovisual quality audit schema no soportado.")
    if audit.get("record_type") != AUDIOVISUAL_QUALITY_RECORD_TYPE:
        raise ValueError("record_type de quality audit inválido.")
    if audit.get("status") != "quality_audit_complete" or not audit.get("valid"):
        raise ValueError("Treatment decision requiere un quality audit completo y válido.")
    if audit.get("treatment_authorized") or audit.get("auto_apply"):
        raise ValueError("El quality audit upstream no puede contener capacidad de tratamiento.")

    binding = audit.get("phase2e_binding")
    if not isinstance(binding, dict):
        raise ValueError("Quality audit sin binding 2E.")
    if binding.get("required_status") != "technical_post_render_pass":
        raise ValueError("Quality audit no conserva el requisito técnico 2E.")
    output_sha = str(binding.get("output_sha256") or "").lower()
    if not _valid_sha256(output_sha):
        raise ValueError("Quality audit sin output SHA-256 válido.")

    findings = audit.get("findings")
    if not isinstance(findings, list):
        raise ValueError("Quality audit sin findings[] auditable.")
    summary = audit.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Quality audit sin summary.")
    risk_count = sum(
        isinstance(item, dict) and item.get("severity") == "risk"
        for item in findings
    )
    if int(summary.get("risk_count") or 0) != risk_count:
        raise ValueError("Quality audit risk_count no coincide con findings[].")


def build_audiovisual_treatment_decision(audit: dict[str, Any]) -> dict[str, Any]:
    """Turn Phase 3 measurements into a fail-safe bypass/review decision.

    This contract deliberately has no treatment parameters and no executable
    capability. A measurement can request evaluation, but it cannot choose a
    loudness target, denoise strength, join crossfade or renderer mutation.
    """
    _validate_quality_audit(audit)
    findings = list(audit.get("findings") or [])
    risks = [
        item for item in findings
        if isinstance(item, dict) and item.get("severity") == "risk"
    ]

    review_topics: list[str] = []
    for finding in risks:
        code = str(finding.get("code") or "")
        if code == "output_true_peak_above_0_dbtp":
            topic = "evaluate_normalization_or_true_peak_policy"
        else:
            topic = "manual_audiovisual_quality_review"
        if topic not in review_topics:
            review_topics.append(topic)

    if risks:
        status = "treatment_review_required"
        rationale = (
            "El audit contiene uno o más riesgos medidos. Se requiere revisión y evidencia específica "
            "antes de definir parámetros o tratamiento."
        )
    else:
        status = "bypass_preserve_render"
        rationale = (
            "El audit no contiene riesgos medidos que justifiquen procesamiento. Se preserva el render "
            "sin normalización, denoise ni smoothing por defecto."
        )

    binding = audit["phase2e_binding"]
    return {
        "schema_version": AUDIOVISUAL_TREATMENT_SCHEMA_VERSION,
        "record_type": AUDIOVISUAL_TREATMENT_RECORD_TYPE,
        "status": status,
        "quality_audit_binding": {
            "output_sha256": binding["output_sha256"],
            "technical_report_sha256": binding.get("technical_report_sha256"),
            "risk_count": len(risks),
        },
        "review_required": bool(risks),
        "review_topics": review_topics,
        "rationale": rationale,
        "treatment_policy": {
            "normalization": "not_authorized",
            "denoise": "not_authorized",
            "join_smoothing": "not_authorized",
            "parameters_defined": False,
            "mandatory_treatment": False,
        },
        "executable": False,
        "treatment_authorized": False,
        "auto_apply": False,
    }
