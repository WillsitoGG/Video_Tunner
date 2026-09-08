from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approval import evidence_fingerprint
from .denoise_plan import validate_denoise_plan_proposal


DENOISE_EXECUTION_AUTHORIZATION_SCHEMA_VERSION = 1
DENOISE_EXECUTION_AUTHORIZATION_RECORD_TYPE = "denoise_execution_authorization"
DENOISE_EXECUTION_AUTHORIZATION_DECISIONS = {"APPROVE", "REJECT"}


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _normalise_sha(value: str, *, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not _valid_sha256(digest):
        raise ValueError(f"{label} debe ser un SHA-256 válido.")
    return digest


def denoise_execution_snapshot(
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    plan_sha256: str,
    current_output_sha256: str,
) -> dict[str, Any]:
    """Return the exact non-executable 3.6h plan eligible for explicit authorization."""
    digests = {
        "noise_audit_sha256": _normalise_sha(noise_audit_sha256, label="noise_audit_sha256"),
        "selection_review_sha256": _normalise_sha(selection_review_sha256, label="selection_review_sha256"),
        "plan_sha256": _normalise_sha(plan_sha256, label="plan_sha256"),
        "current_output_sha256": _normalise_sha(current_output_sha256, label="current_output_sha256"),
    }
    validation = validate_denoise_plan_proposal(
        noise_audit,
        selection_review,
        plan,
        noise_audit_sha256=digests["noise_audit_sha256"],
        selection_review_sha256=digests["selection_review_sha256"],
        current_output_sha256=digests["current_output_sha256"],
    )
    if not validation.get("valid"):
        raise ValueError(f"Denoise plan inválido/stale: {validation.get('status')}: {validation.get('reason')}")
    if not validation.get("ready"):
        raise ValueError("Denoise plan no está listo para execution authorization.")

    bindings = plan.get("bindings")
    policy = plan.get("policy")
    runtime = plan.get("runtime")
    media_contract = plan.get("media_contract")
    if not all(isinstance(value, dict) for value in (bindings, policy, runtime, media_contract)):
        raise ValueError("Denoise plan no contiene bindings/policy/runtime/media_contract válidos.")
    if plan.get("blockers") not in ([], None):
        raise ValueError("Denoise plan contiene blockers.")
    if policy.get("mode") != "selected_deepfilternet_offline_fail_closed":
        raise ValueError("Execution authorization sólo admite el mode DeepFilterNet congelado.")
    if policy.get("noise_evidence_role") != "measurement_coverage_only_not_treatment_trigger":
        raise ValueError("Execution authorization no admite que noise measurement actúe como trigger de tratamiento.")
    if policy.get("explicit_execution_authorization_required") is not True:
        raise ValueError("Denoise plan no conserva autorización explícita obligatoria.")
    if policy.get("runtime_download_allowed") is not False or policy.get("network_access_required") is not False:
        raise ValueError("Denoise plan viola el contrato offline portable.")
    if policy.get("source_overwrite_allowed") is not False or policy.get("product_default") != "preserve":
        raise ValueError("Denoise plan viola preserve/no-overwrite.")
    if runtime.get("arguments_template") != ["--compensate-delay", "--output-dir", "<output_dir>", "<input_wav>"]:
        raise ValueError("Denoise plan no conserva el CLI congelado.")
    if media_contract.get("delay_compensation_required") is not True:
        raise ValueError("Denoise plan no conserva compensate-delay.")
    if float(media_contract.get("raw_duration_delta_max_seconds")) != 0.05:
        raise ValueError("Denoise plan no conserva el límite temporal 3.6g.")

    return {
        "plan_schema_version": plan.get("schema_version"),
        "plan_record_type": plan.get("record_type"),
        "plan_status": plan.get("status"),
        "plan_sha256": digests["plan_sha256"],
        "bindings": deepcopy(bindings),
        "policy": deepcopy(policy),
        "runtime": deepcopy(runtime),
        "media_contract": deepcopy(media_contract),
        "parameters_defined": True,
        "parameters_executable": False,
        "denoise_render_authorization": False,
        "plan_render_authorization": False,
        "renderer_available": False,
        "auto_apply": False,
    }


def build_denoise_execution_authorization(
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    *,
    decision: str,
    actor: str,
    reason: str,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    plan_sha256: str,
    current_output_sha256: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    """Record an explicit APPROVE/REJECT decision for a future gated denoise renderer.

    Even APPROVE is not executable in 3.6h: there is no renderer in this phase.
    The artifact only grants a narrowly bound permission that a later renderer
    must independently revalidate before processing any media.
    """
    normalized_decision = str(decision or "").strip().upper()
    normalized_actor = str(actor or "").strip()
    normalized_reason = str(reason or "").strip()
    if normalized_decision not in DENOISE_EXECUTION_AUTHORIZATION_DECISIONS:
        raise ValueError("decision debe ser APPROVE o REJECT.")
    if not normalized_actor:
        raise ValueError("actor es obligatorio para denoise execution authorization.")
    if not normalized_reason:
        raise ValueError("reason es obligatorio para denoise execution authorization.")

    snapshot = denoise_execution_snapshot(
        noise_audit,
        selection_review,
        plan,
        noise_audit_sha256=noise_audit_sha256,
        selection_review_sha256=selection_review_sha256,
        plan_sha256=plan_sha256,
        current_output_sha256=current_output_sha256,
    )
    fingerprint = evidence_fingerprint(snapshot)
    authorized = normalized_decision == "APPROVE"

    return {
        "schema_version": DENOISE_EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
        "record_type": DENOISE_EXECUTION_AUTHORIZATION_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        "decision": normalized_decision,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "authorization_state": "authorized_for_future_gated_renderer" if authorized else "rejected",
        "authorized": authorized,
        "denoise_render_authorization": authorized,
        "plan_render_authorization": False,
        "parameters_executable": False,
        "renderer_available": False,
        "executable": False,
        "auto_apply": False,
        "plan": {
            "sha256": str(plan_sha256).strip().lower(),
            "schema_version": snapshot["plan_schema_version"],
            "record_type": snapshot["plan_record_type"],
        },
        "quality_output_sha256": snapshot["bindings"]["quality_output_sha256"],
        "selected_candidate_id": snapshot["bindings"]["selected_candidate_id"],
        "runtime_contract_fingerprint": snapshot["bindings"]["runtime_contract_fingerprint"],
        "plan_evidence_fingerprint": fingerprint,
        "plan_evidence_snapshot": snapshot,
    }


def validate_denoise_execution_authorization(
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    plan_sha256: str,
    current_output_sha256: str,
) -> dict[str, Any]:
    base = {
        "valid": False,
        "authorized": False,
        "denoise_render_authorization": False,
        "plan_render_authorization": False,
        "parameters_executable": False,
        "renderer_available": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(authorization, dict):
        return base | {"status": "invalid_record", "reason": "authorization_not_object"}
    if authorization.get("schema_version") != DENOISE_EXECUTION_AUTHORIZATION_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if authorization.get("record_type") != DENOISE_EXECUTION_AUTHORIZATION_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    if authorization.get("plan_render_authorization"):
        return base | {"status": "invalid_record", "reason": "plan_render_authorization_forbidden"}
    if authorization.get("parameters_executable") or authorization.get("renderer_available") or authorization.get("executable") or authorization.get("auto_apply"):
        return base | {"status": "invalid_record", "reason": "authorization_record_must_not_be_executable"}

    decision = str(authorization.get("decision") or "").strip().upper()
    if decision not in DENOISE_EXECUTION_AUTHORIZATION_DECISIONS:
        return base | {"status": "invalid_record", "reason": "invalid_decision"}
    expected_authorized = decision == "APPROVE"
    expected_state = "authorized_for_future_gated_renderer" if expected_authorized else "rejected"
    if authorization.get("authorization_state") != expected_state:
        return base | {"status": "invalid_record", "reason": "decision_state_mismatch"}
    if bool(authorization.get("authorized")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "decision_authorized_mismatch"}
    if bool(authorization.get("denoise_render_authorization")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "render_authorization_mismatch"}
    if not str(authorization.get("actor") or "").strip() or not str(authorization.get("reason") or "").strip():
        return base | {"status": "invalid_record", "reason": "missing_audit_fields"}

    plan_digest = _normalise_sha(plan_sha256, label="plan_sha256")
    recorded_plan = authorization.get("plan")
    if not isinstance(recorded_plan, dict):
        return base | {"status": "invalid_record", "reason": "missing_plan_provenance"}
    if recorded_plan.get("sha256") != plan_digest:
        return base | {"status": "stale_plan", "reason": "plan_sha256_changed"}

    try:
        snapshot = denoise_execution_snapshot(
            noise_audit,
            selection_review,
            plan,
            noise_audit_sha256=noise_audit_sha256,
            selection_review_sha256=selection_review_sha256,
            plan_sha256=plan_sha256,
            current_output_sha256=current_output_sha256,
        )
    except (ValueError, TypeError) as exc:
        return base | {"status": "stale_or_invalid_plan", "reason": str(exc)}

    fingerprint = evidence_fingerprint(snapshot)
    if authorization.get("plan_evidence_fingerprint") != fingerprint:
        return base | {"status": "stale_evidence", "reason": "plan_evidence_fingerprint_changed"}
    if authorization.get("plan_evidence_snapshot") != snapshot:
        return base | {"status": "stale_evidence", "reason": "plan_evidence_snapshot_changed"}
    if authorization.get("quality_output_sha256") != snapshot["bindings"]["quality_output_sha256"]:
        return base | {"status": "invalid_record", "reason": "quality_output_sha256_mismatch"}
    if authorization.get("selected_candidate_id") != snapshot["bindings"]["selected_candidate_id"]:
        return base | {"status": "invalid_record", "reason": "selected_candidate_id_mismatch"}
    if authorization.get("runtime_contract_fingerprint") != snapshot["bindings"]["runtime_contract_fingerprint"]:
        return base | {"status": "invalid_record", "reason": "runtime_contract_fingerprint_mismatch"}

    return base | {
        "status": "valid_authorized" if expected_authorized else "valid_rejected",
        "reason": None,
        "valid": True,
        "authorized": expected_authorized,
        "denoise_render_authorization": expected_authorized,
        "quality_output_sha256": snapshot["bindings"]["quality_output_sha256"],
        "selected_candidate_id": snapshot["bindings"]["selected_candidate_id"],
        "runtime_contract_fingerprint": snapshot["bindings"]["runtime_contract_fingerprint"],
        "plan_evidence_fingerprint": fingerprint,
    }


def save_denoise_execution_authorization(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
