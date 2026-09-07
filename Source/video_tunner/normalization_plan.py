from __future__ import annotations

import math
from typing import Any

from .normalization_approval import validate_normalization_approval

NORMALIZATION_PLAN_SCHEMA_VERSION = 1
NORMALIZATION_PLAN_RECORD_TYPE = "normalization_plan_proposal"
FFMPEG_TARGET_LRA_MIN = 1.0
FFMPEG_TARGET_LRA_MAX = 50.0


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _validate_quality_audit(audit: dict[str, Any], *, quality_audit_sha256: str) -> dict[str, float]:
    digest = str(quality_audit_sha256 or "").strip().lower()
    if not _valid_sha256(digest):
        raise ValueError("quality_audit_sha256 debe ser SHA-256 válido.")
    if not isinstance(audit, dict):
        raise ValueError("Quality audit debe ser un objeto JSON.")
    if audit.get("schema_version") != 1 or audit.get("record_type") != "audiovisual_quality_audit":
        raise ValueError("Quality audit schema/record_type no soportado.")
    if audit.get("status") != "quality_audit_complete" or not audit.get("valid"):
        raise ValueError("Normalization plan requiere quality audit completo y válido.")
    if audit.get("treatment_authorized") or audit.get("auto_apply"):
        raise ValueError("Quality audit upstream contiene capability prohibida.")

    binding = audit.get("phase2e_binding")
    measurements = audit.get("measurements")
    if not isinstance(binding, dict) or not isinstance(measurements, dict):
        raise ValueError("Quality audit sin binding/measurements.")
    if binding.get("required_status") != "technical_post_render_pass":
        raise ValueError("Quality audit no conserva technical_post_render_pass.")
    output_sha = str(binding.get("output_sha256") or "").lower()
    if not _valid_sha256(output_sha):
        raise ValueError("Quality audit sin output SHA válido.")

    output_audio = measurements.get("output_audio")
    if not isinstance(output_audio, dict):
        raise ValueError("Quality audit sin output_audio measurements.")
    values = {
        "integrated_lufs": _finite(output_audio.get("integrated_lufs")),
        "true_peak_dbtp": _finite(output_audio.get("true_peak_dbtp")),
        "loudness_range_lu": _finite(output_audio.get("loudness_range_lu")),
        "threshold_lufs": _finite(output_audio.get("threshold_lufs")),
    }
    if any(value is None for value in values.values()):
        raise ValueError("Quality audit no contiene las cuatro mediciones finitas requeridas para two-pass review.")
    return {key: float(value) for key, value in values.items()} | {"output_sha256": output_sha, "quality_audit_sha256": digest}


def build_normalization_plan_proposal(
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
) -> dict[str, Any]:
    """Prepare a non-executable, linear-only normalization proposal.

    Policy: preserve the measured input LRA instead of inventing a product LRA
    target. The proposal is ready only when FFmpeg's documented linear-mode
    constraints are met. If the required loudness gain would violate the selected
    true-peak target, fail closed rather than silently permitting dynamic mode.
    """
    measurements = _validate_quality_audit(
        quality_audit,
        quality_audit_sha256=quality_audit_sha256,
    )
    approval_digest = str(approval_sha256 or "").strip().lower()
    if not _valid_sha256(approval_digest):
        raise ValueError("approval_sha256 debe ser SHA-256 válido.")

    validation = validate_normalization_approval(
        profile_decision,
        approval,
        profile_decision_sha256=profile_decision_sha256,
    )
    if not validation.get("valid"):
        raise ValueError(f"Normalization approval inválido/stale: {validation.get('status')}: {validation.get('reason')}")
    if not validation.get("approved") or not validation.get("normalization_plan_preparation_authorized"):
        raise ValueError("Normalization plan requiere APPROVE vigente.")

    profile = profile_decision.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("Profile decision sin profile.")
    if str(profile_decision.get("quality_output_sha256") or "").lower() != measurements["output_sha256"]:
        raise ValueError("Profile decision y quality audit no apuntan al mismo output SHA.")

    target_i = _finite(profile.get("target_lufs"))
    target_tp = _finite(profile.get("max_true_peak_dbtp"))
    if target_i is None or target_tp is None:
        raise ValueError("El perfil seleccionado no define target loudness/true peak.")

    measured_i = measurements["integrated_lufs"]
    measured_tp = measurements["true_peak_dbtp"]
    measured_lra = measurements["loudness_range_lu"]
    measured_thresh = measurements["threshold_lufs"]
    gain_lu = target_i - measured_i
    predicted_tp = measured_tp + gain_lu

    blockers: list[dict[str, Any]] = []
    if measured_lra < FFMPEG_TARGET_LRA_MIN or measured_lra > FFMPEG_TARGET_LRA_MAX:
        blockers.append(
            {
                "code": "measured_lra_outside_ffmpeg_linear_target_range",
                "measured_lra": measured_lra,
                "allowed_target_min": FFMPEG_TARGET_LRA_MIN,
                "allowed_target_max": FFMPEG_TARGET_LRA_MAX,
            }
        )
    if predicted_tp > target_tp + 1e-9:
        blockers.append(
            {
                "code": "linear_true_peak_constraint_failed",
                "predicted_true_peak_dbtp": round(predicted_tp, 4),
                "target_true_peak_dbtp": target_tp,
                "required_gain_lu": round(gain_lu, 4),
            }
        )

    ready = not blockers
    return {
        "schema_version": NORMALIZATION_PLAN_SCHEMA_VERSION,
        "record_type": NORMALIZATION_PLAN_RECORD_TYPE,
        "status": "linear_normalization_plan_proposal_ready" if ready else "normalization_plan_blocked",
        "ready_for_render_gate_design": ready,
        "bindings": {
            "quality_audit_sha256": measurements["quality_audit_sha256"],
            "profile_decision_sha256": str(profile_decision_sha256).strip().lower(),
            "approval_sha256": approval_digest,
            "quality_output_sha256": measurements["output_sha256"],
            "profile_name": profile.get("name"),
        },
        "policy": {
            "mode": "linear_only_fail_closed",
            "lra_policy": "preserve_measured_lra",
            "dynamic_fallback_allowed": False,
            "reason": "EBU R 128 does not define one universal LRA target; preserve measured LRA and refuse silent FFmpeg dynamic fallback.",
        },
        "measurements": {
            "measured_i": measured_i,
            "measured_tp": measured_tp,
            "measured_lra": measured_lra,
            "measured_thresh": measured_thresh,
        },
        "targets": {
            "target_i": target_i,
            "target_tp": target_tp,
            "target_lra": measured_lra,
            "calculated_linear_gain_lu": round(gain_lu, 4),
            "predicted_linear_true_peak_dbtp": round(predicted_tp, 4),
        },
        "blockers": blockers,
        "parameters_defined": ready,
        "parameters_executable": False,
        "normalization_authorized": False,
        "normalization_render_authorization": False,
        "executable": False,
        "auto_apply": False,
    }


def validate_normalization_plan_proposal(
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
) -> dict[str, Any]:
    """Rebuild and compare the exact 3.5a proposal against current upstream evidence."""
    base = {
        "valid": False,
        "ready": False,
        "parameters_executable": False,
        "normalization_render_authorization": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(plan, dict):
        return base | {"status": "invalid_record", "reason": "plan_not_object"}
    if plan.get("schema_version") != NORMALIZATION_PLAN_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if plan.get("record_type") != NORMALIZATION_PLAN_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    forbidden_true = (
        "parameters_executable",
        "normalization_authorized",
        "normalization_render_authorization",
        "executable",
        "auto_apply",
    )
    if any(bool(plan.get(key)) for key in forbidden_true):
        return base | {"status": "invalid_record", "reason": "unexpected_execution_capability"}
    try:
        expected = build_normalization_plan_proposal(
            quality_audit,
            profile_decision,
            approval,
            quality_audit_sha256=quality_audit_sha256,
            profile_decision_sha256=profile_decision_sha256,
            approval_sha256=approval_sha256,
        )
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_upstream", "reason": str(exc)}
    if plan != expected:
        return base | {"status": "stale_or_tampered_plan", "reason": "plan_no_longer_matches_exact_upstream_rebuild"}
    ready = expected.get("status") == "linear_normalization_plan_proposal_ready" and bool(expected.get("ready_for_render_gate_design"))
    if not ready or expected.get("blockers") not in ([], None) or not expected.get("parameters_defined"):
        return base | {"status": "valid_blocked", "reason": "plan_not_ready_for_execution_authorization", "valid": True}
    return base | {
        "status": "valid_ready",
        "reason": None,
        "valid": True,
        "ready": True,
        "quality_output_sha256": expected["bindings"]["quality_output_sha256"],
        "profile_name": expected["bindings"]["profile_name"],
    }
