from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approval import evidence_fingerprint
from .normalization_plan import validate_normalization_plan_proposal

NORMALIZATION_EXECUTION_AUTHORIZATION_SCHEMA_VERSION = 1
NORMALIZATION_EXECUTION_AUTHORIZATION_RECORD_TYPE = "normalization_execution_authorization"
NORMALIZATION_EXECUTION_AUTHORIZATION_DECISIONS = {"APPROVE", "REJECT"}


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def normalization_execution_snapshot(
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
    plan_sha256: str,
) -> dict[str, Any]:
    """Return the exact 3.5a plan evidence eligible for execution authorization.

    The full upstream chain is rebuilt before the snapshot is accepted. A plan
    that is blocked, stale, tampered or already executable cannot receive an
    execution authorization artifact.
    """
    digests = {
        "quality_audit_sha256": str(quality_audit_sha256 or "").strip().lower(),
        "profile_decision_sha256": str(profile_decision_sha256 or "").strip().lower(),
        "approval_sha256": str(approval_sha256 or "").strip().lower(),
        "plan_sha256": str(plan_sha256 or "").strip().lower(),
    }
    if any(not _valid_sha256(value) for value in digests.values()):
        raise ValueError("Todos los SHA-256 de la cadena de normalización deben ser válidos.")

    validation = validate_normalization_plan_proposal(
        quality_audit,
        profile_decision,
        approval,
        plan,
        quality_audit_sha256=digests["quality_audit_sha256"],
        profile_decision_sha256=digests["profile_decision_sha256"],
        approval_sha256=digests["approval_sha256"],
    )
    if not validation.get("valid"):
        raise ValueError(f"Normalization plan inválido/stale: {validation.get('status')}: {validation.get('reason')}")
    if not validation.get("ready"):
        raise ValueError("Normalization plan no está listo para execution authorization.")

    bindings = plan.get("bindings")
    policy = plan.get("policy")
    measurements = plan.get("measurements")
    targets = plan.get("targets")
    if not all(isinstance(value, dict) for value in (bindings, policy, measurements, targets)):
        raise ValueError("Normalization plan no contiene bindings/policy/measurements/targets válidos.")
    if plan.get("blockers") not in ([], None):
        raise ValueError("Normalization plan contiene blockers.")
    if policy.get("mode") != "linear_only_fail_closed":
        raise ValueError("Execution authorization sólo admite política linear_only_fail_closed.")
    if policy.get("lra_policy") != "preserve_measured_lra":
        raise ValueError("Execution authorization exige preserve_measured_lra.")
    if policy.get("dynamic_fallback_allowed"):
        raise ValueError("Dynamic loudnorm fallback está prohibido.")

    return {
        "plan_schema_version": plan.get("schema_version"),
        "plan_record_type": plan.get("record_type"),
        "plan_status": plan.get("status"),
        "plan_sha256": digests["plan_sha256"],
        "bindings": deepcopy(bindings),
        "policy": deepcopy(policy),
        "measurements": deepcopy(measurements),
        "targets": deepcopy(targets),
        "parameters_defined": True,
        "parameters_executable": False,
        "normalization_render_authorization": False,
        "auto_apply": False,
    }


def build_normalization_execution_authorization(
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    *,
    decision: str,
    actor: str,
    reason: str,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
    plan_sha256: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    """Record the final explicit decision before a normalization render gate exists."""
    normalized_decision = str(decision or "").strip().upper()
    normalized_actor = str(actor or "").strip()
    normalized_reason = str(reason or "").strip()
    if normalized_decision not in NORMALIZATION_EXECUTION_AUTHORIZATION_DECISIONS:
        raise ValueError("decision debe ser APPROVE o REJECT.")
    if not normalized_actor:
        raise ValueError("actor es obligatorio para execution authorization.")
    if not normalized_reason:
        raise ValueError("reason es obligatorio para execution authorization.")

    snapshot = normalization_execution_snapshot(
        quality_audit,
        profile_decision,
        approval,
        plan,
        quality_audit_sha256=quality_audit_sha256,
        profile_decision_sha256=profile_decision_sha256,
        approval_sha256=approval_sha256,
        plan_sha256=plan_sha256,
    )
    fingerprint = evidence_fingerprint(snapshot)
    authorized = normalized_decision == "APPROVE"

    return {
        "schema_version": NORMALIZATION_EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
        "record_type": NORMALIZATION_EXECUTION_AUTHORIZATION_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        "decision": normalized_decision,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "authorization_state": "authorized" if authorized else "rejected",
        "authorized": authorized,
        "normalization_render_authorization": authorized,
        "plan_render_authorization": False,
        "parameters_executable": False,
        "executable": False,
        "auto_apply": False,
        "plan": {
            "sha256": str(plan_sha256).strip().lower(),
            "schema_version": snapshot["plan_schema_version"],
            "record_type": snapshot["plan_record_type"],
        },
        "quality_output_sha256": snapshot["bindings"]["quality_output_sha256"],
        "profile_name": snapshot["bindings"]["profile_name"],
        "plan_evidence_fingerprint": fingerprint,
        "plan_evidence_snapshot": snapshot,
    }


def validate_normalization_execution_authorization(
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
    plan_sha256: str,
) -> dict[str, Any]:
    base = {
        "valid": False,
        "authorized": False,
        "normalization_render_authorization": False,
        "plan_render_authorization": False,
        "parameters_executable": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(authorization, dict):
        return base | {"status": "invalid_record", "reason": "authorization_not_object"}
    if authorization.get("schema_version") != NORMALIZATION_EXECUTION_AUTHORIZATION_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if authorization.get("record_type") != NORMALIZATION_EXECUTION_AUTHORIZATION_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    if authorization.get("plan_render_authorization"):
        return base | {"status": "invalid_record", "reason": "plan_render_authorization_forbidden"}
    if authorization.get("parameters_executable") or authorization.get("executable") or authorization.get("auto_apply"):
        return base | {"status": "invalid_record", "reason": "authorization_record_must_not_be_executable"}

    decision = str(authorization.get("decision") or "").strip().upper()
    if decision not in NORMALIZATION_EXECUTION_AUTHORIZATION_DECISIONS:
        return base | {"status": "invalid_record", "reason": "invalid_decision"}
    expected_authorized = decision == "APPROVE"
    if authorization.get("authorization_state") != ("authorized" if expected_authorized else "rejected"):
        return base | {"status": "invalid_record", "reason": "decision_state_mismatch"}
    if bool(authorization.get("authorized")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "decision_authorized_mismatch"}
    if bool(authorization.get("normalization_render_authorization")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "render_authorization_mismatch"}
    if not str(authorization.get("actor") or "").strip() or not str(authorization.get("reason") or "").strip():
        return base | {"status": "invalid_record", "reason": "missing_audit_fields"}

    plan_digest = str(plan_sha256 or "").strip().lower()
    recorded_plan = authorization.get("plan")
    if not isinstance(recorded_plan, dict):
        return base | {"status": "invalid_record", "reason": "missing_plan_provenance"}
    if recorded_plan.get("sha256") != plan_digest:
        return base | {"status": "stale_plan", "reason": "plan_sha256_changed"}

    try:
        snapshot = normalization_execution_snapshot(
            quality_audit,
            profile_decision,
            approval,
            plan,
            quality_audit_sha256=quality_audit_sha256,
            profile_decision_sha256=profile_decision_sha256,
            approval_sha256=approval_sha256,
            plan_sha256=plan_sha256,
        )
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_plan", "reason": str(exc)}
    fingerprint = evidence_fingerprint(snapshot)
    if authorization.get("plan_evidence_fingerprint") != fingerprint:
        return base | {"status": "stale_evidence", "reason": "plan_evidence_fingerprint_changed"}
    if authorization.get("plan_evidence_snapshot") != snapshot:
        return base | {"status": "stale_evidence", "reason": "plan_evidence_snapshot_changed"}
    if authorization.get("quality_output_sha256") != snapshot["bindings"]["quality_output_sha256"]:
        return base | {"status": "invalid_record", "reason": "quality_output_sha256_mismatch"}
    if authorization.get("profile_name") != snapshot["bindings"]["profile_name"]:
        return base | {"status": "invalid_record", "reason": "profile_name_mismatch"}

    return base | {
        "status": "valid_authorized" if expected_authorized else "valid_rejected",
        "reason": None,
        "valid": True,
        "authorized": expected_authorized,
        "normalization_render_authorization": expected_authorized,
        "quality_output_sha256": snapshot["bindings"]["quality_output_sha256"],
        "profile_name": snapshot["bindings"]["profile_name"],
        "plan_evidence_fingerprint": fingerprint,
    }


def save_normalization_execution_authorization(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
