from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .execution_authorization import validate_execution_authorization

SEMANTIC_PLAN_SCHEMA_VERSION = 1
SEMANTIC_PLAN_RECORD_TYPE = "semantic_edit_plan"


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def semantic_plan_snapshot(
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    *,
    analysis_sha256: str,
    proposal_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    analysis_digest = analysis_sha256.strip().lower()
    proposal_digest = proposal_sha256.strip().lower()
    authorization_digest = authorization_sha256.strip().lower()
    if not all(_valid_sha256(item) for item in (analysis_digest, proposal_digest, authorization_digest)):
        raise ValueError("Los hashes de analysis, proposal y authorization deben ser SHA-256 válidos.")

    validation = validate_execution_authorization(
        analysis,
        proposal,
        authorization,
        analysis_sha256=analysis_digest,
        proposal_sha256=proposal_digest,
    )
    if validation.get("status") != "valid_authorized":
        raise ValueError(
            "La autorización global no está vigente/autorizada: "
            f"{validation.get('status')} ({validation.get('reason')})"
        )
    if not validation.get("edit_plan_materialization_authorized"):
        raise ValueError("La autorización no permite materializar un Semantic Edit Plan.")
    if not validation.get("semantic_render_authorization"):
        raise ValueError("La autorización no incluye semantic render authorization.")

    source = proposal.get("source")
    proposed_edits = proposal.get("proposed_edits")
    if not isinstance(source, dict) or not isinstance(proposed_edits, list) or not proposed_edits:
        raise ValueError("La proposal vigente no contiene source/proposed_edits válidos.")

    edits: list[dict[str, Any]] = []
    for index, proposed in enumerate(proposed_edits, start=1):
        if not isinstance(proposed, dict) or proposed.get("action") != "remove":
            raise ValueError(f"proposed_edit #{index} no es materializable.")
        edits.append(
            {
                "id": f"semantic-edit-{index:04d}",
                "action": "remove",
                "start": float(proposed["start"]),
                "end": float(proposed["end"]),
                "duration": round(float(proposed["end"]) - float(proposed["start"]), 6),
                "candidate_id": proposed.get("candidate_id"),
                "candidate_kind": proposed.get("candidate_kind"),
                "promotion_assessment_id": proposed.get("promotion_assessment_id"),
                "approval_evidence_fingerprint": proposed.get("approval_evidence_fingerprint"),
                "proposal_edit_id": proposed.get("id"),
            }
        )

    duration = float(source["duration_seconds"])
    removed_seconds = round(sum(float(item["duration"]) for item in edits), 6)
    return {
        "source": {
            "file": source.get("file"),
            "duration_seconds": duration,
            "sha256": str(source.get("sha256") or "").lower(),
        },
        "mode": proposal.get("mode"),
        "limits": dict(proposal.get("limits") or {}),
        "provenance": {
            "analysis_sha256": analysis_digest,
            "proposal_sha256": proposal_digest,
            "authorization_sha256": authorization_digest,
            "proposal_evidence_fingerprint": validation.get("proposal_evidence_fingerprint"),
        },
        "edits": edits,
        "summary": {
            "edit_count": len(edits),
            "removed_seconds": removed_seconds,
            "estimated_output_seconds": round(max(0.0, duration - removed_seconds), 6),
        },
    }


def semantic_plan_fingerprint(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def build_semantic_edit_plan(
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    *,
    analysis_sha256: str,
    proposal_sha256: str,
    authorization_sha256: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    snapshot = semantic_plan_snapshot(
        analysis,
        proposal,
        authorization,
        analysis_sha256=analysis_sha256,
        proposal_sha256=proposal_sha256,
        authorization_sha256=authorization_sha256,
    )
    fingerprint = semantic_plan_fingerprint(snapshot)
    return {
        "schema_version": SEMANTIC_PLAN_SCHEMA_VERSION,
        "record_type": SEMANTIC_PLAN_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        **snapshot,
        "plan_fingerprint": fingerprint,
        "globally_authorized": True,
        "requires_semantic_render_gate": True,
        "executable": True,
        "auto_apply": False,
    }


def validate_semantic_edit_plan(
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    plan: dict[str, Any],
    *,
    analysis_sha256: str,
    proposal_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    base = {
        "valid": False,
        "render_gate_ready": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(plan, dict):
        return base | {"status": "invalid_plan", "reason": "plan_not_object"}
    if plan.get("schema_version") != SEMANTIC_PLAN_SCHEMA_VERSION:
        return base | {"status": "invalid_plan", "reason": "unsupported_schema_version"}
    if plan.get("record_type") != SEMANTIC_PLAN_RECORD_TYPE:
        return base | {"status": "invalid_plan", "reason": "invalid_record_type"}
    if "proposed_edits" in plan:
        return base | {"status": "invalid_plan", "reason": "proposal_shape_forbidden"}
    if not plan.get("globally_authorized") or not plan.get("requires_semantic_render_gate"):
        return base | {"status": "invalid_plan", "reason": "missing_global_authorization_contract"}
    if not plan.get("executable") or plan.get("auto_apply"):
        return base | {"status": "invalid_plan", "reason": "execution_capability_contract_mismatch"}

    try:
        current_snapshot = semantic_plan_snapshot(
            analysis,
            proposal,
            authorization,
            analysis_sha256=analysis_sha256,
            proposal_sha256=proposal_sha256,
            authorization_sha256=authorization_sha256,
        )
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_chain", "reason": str(exc)}

    plan_snapshot = {
        "source": plan.get("source"),
        "mode": plan.get("mode"),
        "limits": plan.get("limits"),
        "provenance": plan.get("provenance"),
        "edits": plan.get("edits"),
        "summary": plan.get("summary"),
    }
    current_fingerprint = semantic_plan_fingerprint(current_snapshot)
    if plan.get("plan_fingerprint") != current_fingerprint:
        return base | {"status": "stale_or_tampered_plan", "reason": "plan_fingerprint_changed"}
    if plan_snapshot != current_snapshot:
        return base | {"status": "stale_or_tampered_plan", "reason": "plan_snapshot_changed"}

    return base | {
        "status": "valid_semantic_edit_plan",
        "reason": None,
        "valid": True,
        "render_gate_ready": True,
        "executable": True,
        "plan_fingerprint": current_fingerprint,
        "edit_count": len(current_snapshot["edits"]),
    }


def save_semantic_edit_plan(plan: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
