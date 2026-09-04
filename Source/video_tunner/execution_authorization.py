from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .plan_proposal import GLOBAL_LIMITS, PROPOSAL_READY_STATUS, PROPOSAL_RECORD_TYPE, PROPOSAL_SCHEMA_VERSION

EXECUTION_AUTHORIZATION_SCHEMA_VERSION = 1
EXECUTION_AUTHORIZATION_RECORD_TYPE = "semantic_execution_authorization"
EXECUTION_AUTHORIZATION_DECISIONS = {"APPROVE", "REJECT"}


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _source_snapshot(analysis: dict[str, Any]) -> dict[str, Any]:
    source = analysis.get("source")
    if not isinstance(source, dict):
        raise ValueError("analysis.json no contiene source válido.")
    try:
        duration = float(source["duration_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("analysis.json no contiene duración fuente válida.") from exc
    sha = str(source.get("sha256") or "").lower()
    if duration <= 0.0 or not _valid_sha256(sha):
        raise ValueError("analysis.json contiene provenance fuente inválida.")
    return {
        "file": source.get("file"),
        "duration_seconds": duration,
        "sha256": sha,
    }


def proposal_execution_snapshot(
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    *,
    analysis_sha256: str,
) -> dict[str, Any]:
    """Return the exact bounded proposal evidence eligible for global review.

    The snapshot deliberately validates all non-executable Phase 2E.3 safety
    flags before a global decision can be recorded. A proposal that has been
    mutated to look approved/executable cannot receive an authorization record.
    """
    digest = analysis_sha256.strip().lower()
    if not _valid_sha256(digest):
        raise ValueError("analysis_sha256 debe ser un SHA-256 hexadecimal de 64 caracteres.")

    try:
        analysis_schema = int(analysis.get("schema_version") or 0)
    except (TypeError, ValueError):
        analysis_schema = 0
    if analysis_schema < 9:
        raise ValueError("La autorización requiere analysis schema v9 o superior.")

    if not isinstance(proposal, dict):
        raise ValueError("La proposal no es un objeto JSON.")
    if proposal.get("schema_version") != PROPOSAL_SCHEMA_VERSION:
        raise ValueError("Proposal schema no soportado.")
    if proposal.get("record_type") != PROPOSAL_RECORD_TYPE:
        raise ValueError("Proposal record_type inválido.")
    if proposal.get("status") != PROPOSAL_READY_STATUS:
        raise ValueError("La proposal no está lista para revisión global.")
    if proposal.get("blockers") not in ([], None):
        raise ValueError("La proposal contiene blockers y no puede autorizarse.")
    if not proposal.get("requires_global_review"):
        raise ValueError("La proposal no exige revisión global; contrato inválido.")
    if proposal.get("globally_approved") or proposal.get("render_authorization"):
        raise ValueError("La proposal está mutada como aprobada/renderizable; fail-safe.")
    if proposal.get("executable") or proposal.get("auto_apply"):
        raise ValueError("La proposal contiene capacidad ejecutable inesperada; fail-safe.")
    if proposal.get("analysis_sha256") != digest:
        raise ValueError("La proposal no referencia el analysis SHA-256 actual.")

    source = _source_snapshot(analysis)
    proposal_source = proposal.get("source")
    if not isinstance(proposal_source, dict):
        raise ValueError("La proposal no contiene source válido.")
    expected_proposal_source = {
        "file": proposal_source.get("file"),
        "duration_seconds": float(proposal_source.get("duration_seconds", -1.0)),
        "sha256": str(proposal_source.get("sha256") or "").lower(),
    }
    if expected_proposal_source != source:
        raise ValueError("La source de proposal no coincide con analysis.json.")

    mode = str(analysis.get("mode") or "")
    if mode not in {"conservative", "aggressive"} or proposal.get("mode") != mode:
        raise ValueError("El mode de proposal no coincide con analysis.json.")
    if proposal.get("limits") != GLOBAL_LIMITS:
        raise ValueError("La proposal no conserva los límites globales precomprometidos.")

    proposed_edits = proposal.get("proposed_edits")
    if not isinstance(proposed_edits, list) or not proposed_edits:
        raise ValueError("La proposal no contiene proposed_edits autorizables.")
    previous_end: float | None = None
    normalized_edits: list[dict[str, Any]] = []
    for index, edit in enumerate(proposed_edits, start=1):
        if not isinstance(edit, dict):
            raise ValueError(f"proposed_edit #{index} no es un objeto.")
        if edit.get("action") != "remove":
            raise ValueError(f"proposed_edit #{index} no es una eliminación semántica.")
        if edit.get("globally_approved") or edit.get("render_authorized"):
            raise ValueError(f"proposed_edit #{index} ya declara autorización inesperada.")
        if edit.get("executable") or edit.get("auto_apply"):
            raise ValueError(f"proposed_edit #{index} contiene capacidad ejecutable inesperada.")
        try:
            start = float(edit["start"])
            end = float(edit["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"proposed_edit #{index} contiene timestamps inválidos.") from exc
        if start < 0.0 or end <= start or end > source["duration_seconds"] + 1e-6:
            raise ValueError(f"proposed_edit #{index} queda fuera de la timeline fuente.")
        if previous_end is not None and start < previous_end - 1e-9:
            raise ValueError("La proposal contiene proposed_edits solapados.")
        previous_end = end
        normalized_edits.append(deepcopy(edit))

    summary = proposal.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("La proposal no contiene summary válido.")
    expected_count = len(normalized_edits)
    expected_removed = round(sum(float(item["end"]) - float(item["start"]) for item in normalized_edits), 6)
    expected_fraction = round(expected_removed / source["duration_seconds"], 9)
    if summary.get("proposed_edit_count") != expected_count:
        raise ValueError("proposal summary count no coincide con proposed_edits.")
    if abs(float(summary.get("removed_seconds", -1.0)) - expected_removed) > 1e-6:
        raise ValueError("proposal summary removed_seconds no coincide con proposed_edits.")
    if abs(float(summary.get("removed_fraction", -1.0)) - expected_fraction) > 1e-9:
        raise ValueError("proposal summary removed_fraction no coincide con proposed_edits.")
    if expected_count > int(GLOBAL_LIMITS["max_semantic_edits"]):
        raise ValueError("La proposal excede max_semantic_edits.")
    if expected_removed > float(GLOBAL_LIMITS["max_removed_seconds"]) + 1e-9:
        raise ValueError("La proposal excede max_removed_seconds.")
    if expected_fraction > float(GLOBAL_LIMITS["max_removed_fraction"]) + 1e-12:
        raise ValueError("La proposal excede max_removed_fraction.")

    return {
        "analysis_schema_version": analysis_schema,
        "analysis_sha256": digest,
        "proposal_schema_version": proposal["schema_version"],
        "proposal_record_type": proposal["record_type"],
        "proposal_status": proposal["status"],
        "source": source,
        "mode": mode,
        "limits": deepcopy(GLOBAL_LIMITS),
        "summary": {
            "proposed_edit_count": expected_count,
            "removed_seconds": expected_removed,
            "removed_fraction": expected_fraction,
        },
        "proposed_edits": normalized_edits,
    }


def proposal_execution_fingerprint(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def build_execution_authorization(
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    *,
    decision: str,
    actor: str,
    reason: str,
    analysis_sha256: str,
    proposal_sha256: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    normalized_decision = decision.strip().upper()
    normalized_actor = actor.strip()
    normalized_reason = reason.strip()
    analysis_digest = analysis_sha256.strip().lower()
    proposal_digest = proposal_sha256.strip().lower()
    if normalized_decision not in EXECUTION_AUTHORIZATION_DECISIONS:
        raise ValueError("decision debe ser APPROVE o REJECT.")
    if not normalized_actor:
        raise ValueError("actor es obligatorio para autorización global auditable.")
    if not normalized_reason:
        raise ValueError("reason es obligatorio para autorización global auditable.")
    if not _valid_sha256(analysis_digest) or not _valid_sha256(proposal_digest):
        raise ValueError("analysis_sha256 y proposal_sha256 deben ser SHA-256 válidos.")

    snapshot = proposal_execution_snapshot(
        analysis,
        proposal,
        analysis_sha256=analysis_digest,
    )
    fingerprint = proposal_execution_fingerprint(snapshot)
    authorized = normalized_decision == "APPROVE"

    return {
        "schema_version": EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
        "record_type": EXECUTION_AUTHORIZATION_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        "decision": normalized_decision,
        "actor": normalized_actor,
        "reason": normalized_reason,
        "analysis": {
            "sha256": analysis_digest,
            "schema_version": snapshot["analysis_schema_version"],
        },
        "proposal": {
            "sha256": proposal_digest,
            "schema_version": snapshot["proposal_schema_version"],
            "record_type": snapshot["proposal_record_type"],
        },
        "proposal_evidence_fingerprint": fingerprint,
        "proposal_evidence_snapshot": snapshot,
        "authorization_state": "authorized" if authorized else "rejected",
        "authorized": authorized,
        "edit_plan_materialization_authorized": authorized,
        "semantic_render_authorization": authorized,
        "proposal_render_authorization": False,
        "executable": False,
        "auto_apply": False,
    }


def validate_execution_authorization(
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    *,
    analysis_sha256: str,
    proposal_sha256: str,
) -> dict[str, Any]:
    base = {
        "valid": False,
        "authorized": False,
        "edit_plan_materialization_authorized": False,
        "semantic_render_authorization": False,
        "proposal_render_authorization": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(authorization, dict):
        return base | {"status": "invalid_record", "reason": "authorization_not_object"}
    if authorization.get("schema_version") != EXECUTION_AUTHORIZATION_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if authorization.get("record_type") != EXECUTION_AUTHORIZATION_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    if authorization.get("proposal_render_authorization"):
        return base | {"status": "invalid_record", "reason": "proposal_render_authorization_forbidden"}
    if authorization.get("executable") or authorization.get("auto_apply"):
        return base | {"status": "invalid_record", "reason": "authorization_record_must_not_be_executable"}

    decision = str(authorization.get("decision") or "").upper()
    if decision not in EXECUTION_AUTHORIZATION_DECISIONS:
        return base | {"status": "invalid_record", "reason": "invalid_decision"}
    expected_authorized = decision == "APPROVE"
    expected_state = "authorized" if expected_authorized else "rejected"
    if authorization.get("authorization_state") != expected_state:
        return base | {"status": "invalid_record", "reason": "decision_state_mismatch"}
    if bool(authorization.get("authorized")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "decision_authorized_mismatch"}
    if bool(authorization.get("edit_plan_materialization_authorized")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "materialization_capability_mismatch"}
    if bool(authorization.get("semantic_render_authorization")) != expected_authorized:
        return base | {"status": "invalid_record", "reason": "render_capability_mismatch"}
    if not str(authorization.get("actor") or "").strip() or not str(authorization.get("reason") or "").strip():
        return base | {"status": "invalid_record", "reason": "missing_audit_fields"}

    analysis_digest = analysis_sha256.strip().lower()
    proposal_digest = proposal_sha256.strip().lower()
    recorded_analysis = authorization.get("analysis")
    recorded_proposal = authorization.get("proposal")
    if not isinstance(recorded_analysis, dict) or not isinstance(recorded_proposal, dict):
        return base | {"status": "invalid_record", "reason": "missing_provenance"}
    if recorded_analysis.get("sha256") != analysis_digest:
        return base | {"status": "stale_analysis", "reason": "analysis_sha256_changed"}
    if recorded_proposal.get("sha256") != proposal_digest:
        return base | {"status": "stale_proposal", "reason": "proposal_sha256_changed"}

    try:
        current_snapshot = proposal_execution_snapshot(
            analysis,
            proposal,
            analysis_sha256=analysis_digest,
        )
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_proposal", "reason": str(exc)}

    current_fingerprint = proposal_execution_fingerprint(current_snapshot)
    if authorization.get("proposal_evidence_fingerprint") != current_fingerprint:
        return base | {"status": "stale_evidence", "reason": "proposal_evidence_fingerprint_changed"}
    if authorization.get("proposal_evidence_snapshot") != current_snapshot:
        return base | {"status": "stale_evidence", "reason": "proposal_evidence_snapshot_changed"}

    return base | {
        "status": "valid_authorized" if expected_authorized else "valid_rejected",
        "reason": None,
        "valid": True,
        "authorized": expected_authorized,
        "edit_plan_materialization_authorized": expected_authorized,
        "semantic_render_authorization": expected_authorized,
        "proposal_evidence_fingerprint": current_fingerprint,
    }


def save_execution_authorization(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
