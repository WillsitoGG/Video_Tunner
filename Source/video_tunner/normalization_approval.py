from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approval import evidence_fingerprint
from .normalization_profiles import DEFAULT_NORMALIZATION_PROFILE

NORMALIZATION_APPROVAL_SCHEMA_VERSION = 1
NORMALIZATION_APPROVAL_RECORD_TYPE = "normalization_approval"
NORMALIZATION_APPROVAL_DECISIONS = {"APPROVE", "REJECT"}


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def normalization_profile_snapshot(profile_decision: dict[str, Any]) -> dict[str, Any]:
    """Return the exact non-preserve profile decision eligible for human approval."""
    if not isinstance(profile_decision, dict):
        raise ValueError("Normalization profile decision debe ser un objeto JSON.")
    if profile_decision.get("schema_version") != 1:
        raise ValueError("Normalization profile decision schema no soportado.")
    if profile_decision.get("record_type") != "normalization_profile_decision":
        raise ValueError("Normalization profile decision record_type inválido.")
    if profile_decision.get("status") != "normalization_profile_review_selected":
        raise ValueError("Sólo un perfil no-preserve seleccionado para review puede recibir approval.")
    if not profile_decision.get("explicit_opt_in_required"):
        raise ValueError("El perfil no acredita explicit_opt_in_required=true.")
    if not profile_decision.get("human_approval_required"):
        raise ValueError("El perfil no exige human approval.")
    if not profile_decision.get("normalization_requested"):
        raise ValueError("El perfil no contiene normalization_requested=true.")
    if (
        profile_decision.get("normalization_authorized")
        or profile_decision.get("parameters_executable")
        or profile_decision.get("render_authorized")
        or profile_decision.get("auto_apply")
    ):
        raise ValueError("Profile decision upstream contiene capacidad prohibida.")

    profile = profile_decision.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("Profile decision sin profile válido.")
    profile_name = str(profile.get("name") or "")
    if not profile_name or profile_name == DEFAULT_NORMALIZATION_PROFILE:
        raise ValueError("El perfil preserve no requiere normalization approval.")
    output_sha = str(profile_decision.get("quality_output_sha256") or "").lower()
    if not _valid_sha256(output_sha):
        raise ValueError("Profile decision sin quality output SHA-256 válido.")

    return {
        "profile_decision_schema_version": 1,
        "quality_output_sha256": output_sha,
        "profile": profile,
        "explicit_opt_in_required": True,
        "human_approval_required": True,
        "normalization_requested": True,
    }


def build_normalization_approval(
    profile_decision: dict[str, Any],
    *,
    decision: str,
    actor: str,
    reason: str,
    profile_decision_sha256: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    """Create explicit human APPROVE/REJECT for one exact normalization profile decision.

    APPROVE only allows preparation of the next normalization-planning gate. It
    never authorizes FFmpeg treatment, executable parameters, semantic edits or
    auto-apply.
    """
    normalized_decision = str(decision or "").strip().upper()
    normalized_actor = str(actor or "").strip()
    normalized_reason = str(reason or "").strip()
    digest = str(profile_decision_sha256 or "").strip().lower()
    if normalized_decision not in NORMALIZATION_APPROVAL_DECISIONS:
        raise ValueError("decision debe ser APPROVE o REJECT.")
    if not normalized_actor:
        raise ValueError("actor es obligatorio.")
    if not normalized_reason:
        raise ValueError("reason es obligatorio.")
    if not _valid_sha256(digest):
        raise ValueError("profile_decision_sha256 debe ser SHA-256 válido.")

    snapshot = normalization_profile_snapshot(profile_decision)
    fingerprint = evidence_fingerprint(snapshot)
    approved = normalized_decision == "APPROVE"
    return {
        "schema_version": NORMALIZATION_APPROVAL_SCHEMA_VERSION,
        "record_type": NORMALIZATION_APPROVAL_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        "profile_decision": {
            "sha256": digest,
            "evidence_fingerprint": fingerprint,
        },
        "quality_output_sha256": snapshot["quality_output_sha256"],
        "profile_name": snapshot["profile"]["name"],
        "decision": normalized_decision,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "approval_state": "approved" if approved else "rejected",
        "approved": approved,
        "normalization_plan_preparation_authorized": approved,
        "normalization_authorized": False,
        "normalization_render_authorization": False,
        "parameters_executable": False,
        "executable": False,
        "auto_apply": False,
        "evidence_snapshot": snapshot,
    }


def validate_normalization_approval(
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    *,
    profile_decision_sha256: str,
) -> dict[str, Any]:
    base = {
        "valid": False,
        "approved": False,
        "normalization_plan_preparation_authorized": False,
        "normalization_authorized": False,
        "normalization_render_authorization": False,
        "parameters_executable": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(approval, dict):
        return base | {"status": "invalid_record", "reason": "approval_not_object"}
    if approval.get("schema_version") != NORMALIZATION_APPROVAL_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if approval.get("record_type") != NORMALIZATION_APPROVAL_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}

    forbidden_true = (
        "normalization_authorized",
        "normalization_render_authorization",
        "parameters_executable",
        "executable",
        "auto_apply",
    )
    if any(bool(approval.get(key)) for key in forbidden_true):
        return base | {"status": "invalid_record", "reason": "unexpected_execution_capability"}

    decision = str(approval.get("decision") or "").upper()
    if decision not in NORMALIZATION_APPROVAL_DECISIONS:
        return base | {"status": "invalid_record", "reason": "invalid_decision"}
    expected_approved = decision == "APPROVE"
    if bool(approval.get("approved")) != expected_approved:
        return base | {"status": "invalid_record", "reason": "decision_approved_mismatch"}
    if approval.get("approval_state") != ("approved" if expected_approved else "rejected"):
        return base | {"status": "invalid_record", "reason": "decision_state_mismatch"}
    if bool(approval.get("normalization_plan_preparation_authorized")) != expected_approved:
        return base | {"status": "invalid_record", "reason": "preparation_authorization_mismatch"}
    if not str(approval.get("actor") or "").strip() or not str(approval.get("reason") or "").strip():
        return base | {"status": "invalid_record", "reason": "missing_audit_fields"}

    current_digest = str(profile_decision_sha256 or "").strip().lower()
    if not _valid_sha256(current_digest):
        return base | {"status": "invalid_record", "reason": "invalid_current_profile_sha256"}
    provenance = approval.get("profile_decision")
    if not isinstance(provenance, dict):
        return base | {"status": "invalid_record", "reason": "missing_profile_provenance"}
    if provenance.get("sha256") != current_digest:
        return base | {"status": "stale_profile_decision", "reason": "profile_decision_sha256_changed"}

    try:
        snapshot = normalization_profile_snapshot(profile_decision)
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_profile", "reason": str(exc)}
    fingerprint = evidence_fingerprint(snapshot)
    if provenance.get("evidence_fingerprint") != fingerprint:
        return base | {"status": "stale_profile_decision", "reason": "profile_fingerprint_changed"}
    if approval.get("evidence_snapshot") != snapshot:
        return base | {"status": "stale_profile_decision", "reason": "profile_snapshot_changed"}
    if approval.get("quality_output_sha256") != snapshot["quality_output_sha256"]:
        return base | {"status": "invalid_record", "reason": "quality_output_sha256_mismatch"}
    if approval.get("profile_name") != snapshot["profile"]["name"]:
        return base | {"status": "invalid_record", "reason": "profile_name_mismatch"}

    return base | {
        "status": "valid_approved" if expected_approved else "valid_rejected",
        "reason": None,
        "valid": True,
        "approved": expected_approved,
        "normalization_plan_preparation_authorized": expected_approved,
        "quality_output_sha256": snapshot["quality_output_sha256"],
        "profile_name": snapshot["profile"]["name"],
        "evidence_fingerprint": fingerprint,
    }


def save_normalization_approval(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
