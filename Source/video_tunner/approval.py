from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPROVAL_SCHEMA_VERSION = 1
APPROVAL_RECORD_TYPE = "promotion_approval"
APPROVAL_DECISIONS = {"APPROVE", "REJECT"}
PROMOTION_REVIEW_STATUS = "eligible_for_promotion_review"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"El JSON no contiene un objeto: {path}")
    return payload


def _unique_by_id(items: Any, identifier: str, *, label: str) -> dict[str, Any]:
    if not isinstance(items, list):
        raise ValueError(f"analysis.json no contiene {label} como lista.")
    matches = [item for item in items if isinstance(item, dict) and item.get("id") == identifier]
    if len(matches) != 1:
        raise ValueError(f"Referencia {label} no única o inexistente: {identifier}")
    return matches[0]


def promotion_evidence_snapshot(
    analysis: dict[str, Any],
    promotion_assessment_id: str,
) -> dict[str, Any]:
    """Return the exact review evidence that an explicit approval can bind to.

    A snapshot can only be built for a Phase 2E.1 review candidate. Upstream
    blockers or tampered promotion records fail closed and cannot receive an
    approval artifact.
    """
    try:
        schema_version = int(analysis.get("schema_version") or 0)
    except (TypeError, ValueError):
        schema_version = 0
    if schema_version < 9:
        raise ValueError("La aprobación requiere analysis schema v9 o superior.")

    promotion = _unique_by_id(
        analysis.get("promotion_assessments"),
        promotion_assessment_id,
        label="promotion_assessments",
    )
    if promotion.get("status") != PROMOTION_REVIEW_STATUS:
        raise ValueError("La promotion assessment no es elegible para revisión de promoción.")
    if not promotion.get("promotion_review_candidate"):
        raise ValueError("La promotion assessment no acredita promotion_review_candidate=true.")
    if not promotion.get("requires_explicit_approval"):
        raise ValueError("La promotion assessment no exige aprobación explícita; contrato inválido.")
    if promotion.get("approved") or promotion.get("edit") is not None:
        raise ValueError("La promotion assessment está mutada como aprobada/editable; fail-safe.")
    if promotion.get("safe_for_cut") or promotion.get("executable") or promotion.get("auto_apply"):
        raise ValueError("La promotion assessment contiene capacidad ejecutable inesperada; fail-safe.")

    candidate_id = str(promotion.get("candidate_id") or "")
    eligibility_id = str(promotion.get("eligibility_assessment_id") or "")
    candidate = _unique_by_id(analysis.get("candidates"), candidate_id, label="candidates")
    eligibility = _unique_by_id(
        analysis.get("eligibility_assessments"),
        eligibility_id,
        label="eligibility_assessments",
    )

    candidate_kind = str(candidate.get("kind") or "")
    if candidate_kind != str(promotion.get("candidate_kind") or ""):
        raise ValueError("candidate_kind no coincide con promotion assessment.")
    if candidate_id != str(eligibility.get("candidate_id") or ""):
        raise ValueError("candidate_id no coincide entre promotion y eligibility.")
    if candidate_kind != str(eligibility.get("candidate_kind") or ""):
        raise ValueError("candidate_kind no coincide entre candidate y eligibility.")
    if eligibility.get("status") != "foundation_guards_pass":
        raise ValueError("La eligibility upstream ya no es foundation_guards_pass.")
    if not eligibility.get("future_promotion_candidate"):
        raise ValueError("La eligibility upstream ya no es future_promotion_candidate.")

    removed = eligibility.get("removed_text_validation")
    if not isinstance(removed, dict) or not removed.get("valid"):
        raise ValueError("removed_text_validation upstream ya no es válida.")

    target = promotion.get("target_preview")
    if not isinstance(target, dict):
        raise ValueError("La promotion assessment no contiene target_preview válido.")

    expected_target = {
        "source": removed.get("source"),
        "text": removed.get("text"),
        "start": removed.get("start"),
        "end": removed.get("end"),
        "word_start_index": removed.get("word_start_index"),
        "word_end_index_exclusive": removed.get("word_end_index_exclusive"),
    }
    if target != expected_target:
        raise ValueError("target_preview no coincide con removed_text_validation upstream.")

    return {
        "analysis_schema_version": schema_version,
        "candidate_id": candidate_id,
        "candidate_kind": candidate_kind,
        "eligibility_assessment_id": eligibility_id,
        "eligibility_status": eligibility.get("status"),
        "promotion_assessment_id": promotion_assessment_id,
        "promotion_status": promotion.get("status"),
        "mode": promotion.get("mode"),
        "target": deepcopy(target),
    }


def evidence_fingerprint(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def build_approval_record(
    analysis: dict[str, Any],
    promotion_assessment_id: str,
    *,
    decision: str,
    actor: str,
    reason: str,
    analysis_sha256: str | None = None,
    created_utc: str | None = None,
) -> dict[str, Any]:
    """Create an explicit human approval/rejection artifact, never an edit.

    Phase 2E.2 approvals bind to an immutable snapshot and optional full-file
    analysis SHA-256. Even a valid APPROVE record is not Edit Plan authorization.
    """
    normalized_decision = decision.strip().upper()
    normalized_actor = actor.strip()
    normalized_reason = reason.strip()
    if normalized_decision not in APPROVAL_DECISIONS:
        raise ValueError("decision debe ser APPROVE o REJECT.")
    if not normalized_actor:
        raise ValueError("actor es obligatorio para una aprobación explícita auditable.")
    if not normalized_reason:
        raise ValueError("reason es obligatorio para una aprobación explícita auditable.")
    if analysis_sha256 is not None:
        digest = analysis_sha256.strip().lower()
        if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise ValueError("analysis_sha256 debe ser un SHA-256 hexadecimal de 64 caracteres.")
        analysis_sha256 = digest

    snapshot = promotion_evidence_snapshot(analysis, promotion_assessment_id)
    fingerprint = evidence_fingerprint(snapshot)
    approved = normalized_decision == "APPROVE"

    return {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "record_type": APPROVAL_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        "analysis": {
            "sha256": analysis_sha256,
            "schema_version": snapshot["analysis_schema_version"],
        },
        "promotion_assessment_id": promotion_assessment_id,
        "candidate_id": snapshot["candidate_id"],
        "candidate_kind": snapshot["candidate_kind"],
        "decision": normalized_decision,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "evidence_fingerprint": fingerprint,
        "evidence_snapshot": snapshot,
        "approval_state": "approved" if approved else "rejected",
        "approved": approved,
        "edit_plan_authorization": False,
        "edit": None,
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def validate_approval_record(
    analysis: dict[str, Any],
    approval: dict[str, Any],
    *,
    analysis_sha256: str | None = None,
) -> dict[str, Any]:
    """Validate an approval against current analysis and diagnose staleness."""
    base = {
        "valid": False,
        "approved": False,
        "edit_plan_authorization": False,
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(approval, dict):
        return base | {"status": "invalid_record", "reason": "approval_not_object"}
    if approval.get("schema_version") != APPROVAL_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if approval.get("record_type") != APPROVAL_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    if approval.get("edit_plan_authorization") or approval.get("edit") is not None:
        return base | {"status": "invalid_record", "reason": "unexpected_edit_authorization"}
    if approval.get("safe_for_cut") or approval.get("executable") or approval.get("auto_apply"):
        return base | {"status": "invalid_record", "reason": "unexpected_execution_capability"}

    decision = str(approval.get("decision") or "").upper()
    expected_approved = decision == "APPROVE"
    if decision not in APPROVAL_DECISIONS:
        return base | {"status": "invalid_record", "reason": "invalid_decision"}
    if bool(approval.get("approved")) != expected_approved:
        return base | {"status": "invalid_record", "reason": "decision_approved_mismatch"}
    if approval.get("approval_state") != ("approved" if expected_approved else "rejected"):
        return base | {"status": "invalid_record", "reason": "decision_state_mismatch"}
    if not str(approval.get("actor") or "").strip() or not str(approval.get("reason") or "").strip():
        return base | {"status": "invalid_record", "reason": "missing_audit_fields"}

    recorded_analysis = approval.get("analysis")
    if not isinstance(recorded_analysis, dict):
        return base | {"status": "invalid_record", "reason": "missing_analysis_provenance"}
    recorded_sha = recorded_analysis.get("sha256")
    if analysis_sha256 is not None and recorded_sha != analysis_sha256.lower():
        return base | {"status": "stale_analysis", "reason": "analysis_sha256_changed"}

    promotion_id = str(approval.get("promotion_assessment_id") or "")
    try:
        current_snapshot = promotion_evidence_snapshot(analysis, promotion_id)
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_reference", "reason": str(exc)}

    current_fingerprint = evidence_fingerprint(current_snapshot)
    if approval.get("evidence_fingerprint") != current_fingerprint:
        return base | {"status": "stale_evidence", "reason": "evidence_fingerprint_changed"}
    if approval.get("evidence_snapshot") != current_snapshot:
        return base | {"status": "stale_evidence", "reason": "evidence_snapshot_changed"}
    if approval.get("candidate_id") != current_snapshot["candidate_id"]:
        return base | {"status": "invalid_record", "reason": "candidate_id_mismatch"}
    if approval.get("candidate_kind") != current_snapshot["candidate_kind"]:
        return base | {"status": "invalid_record", "reason": "candidate_kind_mismatch"}

    return base | {
        "status": "valid_approved" if expected_approved else "valid_rejected",
        "reason": None,
        "valid": True,
        "approved": expected_approved,
        "promotion_assessment_id": promotion_id,
        "candidate_id": current_snapshot["candidate_id"],
        "evidence_fingerprint": current_fingerprint,
    }


def save_approval_record(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
