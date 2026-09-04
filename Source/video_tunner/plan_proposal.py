from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approval import validate_approval_record

PROPOSAL_SCHEMA_VERSION = 1
PROPOSAL_RECORD_TYPE = "approved_edit_plan_proposal"
SUPPORTED_CANDIDATE_KINDS = frozenset({"possible_repetition"})

# Phase 2E.3 safety envelope. Deliberately identical for conservative/aggressive
# until broader human evidence justifies a mode-specific expansion.
GLOBAL_LIMITS = {
    "max_semantic_edits": 10,
    "max_removed_seconds": 30.0,
    "max_removed_fraction": 0.05,
}

PROPOSAL_READY_STATUS = "proposal_ready_for_global_review"


def _blocked(
    *,
    analysis_sha256: str,
    source: dict[str, Any],
    mode: str,
    status: str,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "record_type": PROPOSAL_RECORD_TYPE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "analysis_sha256": analysis_sha256,
        "source": source,
        "mode": mode,
        "limits": dict(GLOBAL_LIMITS),
        "blockers": blockers,
        "proposed_edits": [],
        "summary": {
            "proposed_edit_count": 0,
            "removed_seconds": 0.0,
            "removed_fraction": 0.0,
        },
        "requires_global_review": True,
        "globally_approved": False,
        "render_authorization": False,
        "executable": False,
        "auto_apply": False,
    }


def _source_block(analysis: dict[str, Any]) -> tuple[dict[str, Any], float]:
    source = analysis.get("source")
    if not isinstance(source, dict):
        raise ValueError("analysis.json no contiene source válido.")
    try:
        duration = float(source["duration_seconds"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("analysis.json no contiene duración fuente válida.") from exc
    if duration <= 0.0:
        raise ValueError("La duración fuente debe ser positiva.")
    sha = str(source.get("sha256") or "")
    if len(sha) != 64:
        raise ValueError("analysis.json no contiene SHA-256 fuente válido.")
    return {
        "file": source.get("file"),
        "duration_seconds": duration,
        "sha256": sha,
    }, duration


def build_approved_edit_plan_proposal(
    analysis: dict[str, Any],
    approvals: list[dict[str, Any]],
    *,
    analysis_sha256: str,
) -> dict[str, Any]:
    """Build a globally bounded, non-executable proposal from valid approvals.

    Every supplied approval must currently validate as `valid_approved`. A stale,
    rejected, invalid or duplicated record vetoes the whole proposal. Successful
    output uses `proposed_edits`, intentionally not the executable Edit Plan key
    `edits`, and therefore remains separated from render authorization.
    """
    digest = analysis_sha256.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("analysis_sha256 debe ser un SHA-256 hexadecimal de 64 caracteres.")

    try:
        analysis_schema = int(analysis.get("schema_version") or 0)
    except (TypeError, ValueError):
        analysis_schema = 0
    if analysis_schema < 9:
        raise ValueError("La propuesta requiere analysis schema v9 o superior.")

    source, duration = _source_block(analysis)
    mode = str(analysis.get("mode") or "")
    if mode not in {"conservative", "aggressive"}:
        raise ValueError(f"Modo de analysis no soportado: {mode!r}")

    if not approvals:
        return _blocked(
            analysis_sha256=digest,
            source=source,
            mode=mode,
            status="blocked_no_approved_records",
            blockers=[{"reason": "no_approval_records_supplied"}],
        )

    proposed: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    seen_promotions: set[str] = set()
    seen_candidates: set[str] = set()

    for index, approval in enumerate(approvals, start=1):
        validation = validate_approval_record(
            analysis,
            approval,
            analysis_sha256=digest,
        )
        if validation.get("status") != "valid_approved" or not validation.get("approved"):
            blockers.append(
                {
                    "approval_index": index,
                    "promotion_assessment_id": approval.get("promotion_assessment_id"),
                    "reason": "approval_not_currently_valid_approved",
                    "validation_status": validation.get("status"),
                    "validation_reason": validation.get("reason"),
                }
            )
            continue

        promotion_id = str(validation.get("promotion_assessment_id") or "")
        candidate_id = str(validation.get("candidate_id") or "")
        if promotion_id in seen_promotions or candidate_id in seen_candidates:
            blockers.append(
                {
                    "approval_index": index,
                    "promotion_assessment_id": promotion_id,
                    "candidate_id": candidate_id,
                    "reason": "duplicate_approved_target",
                }
            )
            continue
        seen_promotions.add(promotion_id)
        seen_candidates.add(candidate_id)

        snapshot = approval.get("evidence_snapshot") or {}
        candidate_kind = str(snapshot.get("candidate_kind") or "")
        if candidate_kind not in SUPPORTED_CANDIDATE_KINDS:
            blockers.append(
                {
                    "approval_index": index,
                    "candidate_id": candidate_id,
                    "reason": "candidate_kind_not_supported_by_phase2e3",
                    "candidate_kind": candidate_kind,
                }
            )
            continue

        target = snapshot.get("target")
        if not isinstance(target, dict):
            blockers.append(
                {
                    "approval_index": index,
                    "candidate_id": candidate_id,
                    "reason": "missing_approved_target",
                }
            )
            continue
        try:
            start = float(target["start"])
            end = float(target["end"])
        except (KeyError, TypeError, ValueError):
            blockers.append(
                {
                    "approval_index": index,
                    "candidate_id": candidate_id,
                    "reason": "invalid_approved_target_timestamps",
                }
            )
            continue
        if start < 0.0 or end <= start or end > duration + 1e-6:
            blockers.append(
                {
                    "approval_index": index,
                    "candidate_id": candidate_id,
                    "reason": "approved_target_outside_source_timeline",
                    "start": start,
                    "end": end,
                    "source_duration": duration,
                }
            )
            continue

        proposed.append(
            {
                "id": f"proposed-edit-{index:04d}",
                "action": "remove",
                "start": start,
                "end": end,
                "duration": round(end - start, 6),
                "candidate_id": candidate_id,
                "candidate_kind": candidate_kind,
                "promotion_assessment_id": promotion_id,
                "approval_evidence_fingerprint": validation.get("evidence_fingerprint"),
                "approved_target": dict(target),
                "globally_approved": False,
                "render_authorized": False,
                "executable": False,
                "auto_apply": False,
            }
        )

    if blockers:
        return _blocked(
            analysis_sha256=digest,
            source=source,
            mode=mode,
            status="blocked_invalid_or_conflicting_approval",
            blockers=blockers,
        )

    proposed.sort(key=lambda item: (float(item["start"]), float(item["end"]), item["id"]))
    for previous, current in zip(proposed, proposed[1:]):
        if float(current["start"]) < float(previous["end"]) - 1e-9:
            return _blocked(
                analysis_sha256=digest,
                source=source,
                mode=mode,
                status="blocked_overlapping_approved_targets",
                blockers=[
                    {
                        "reason": "approved_targets_overlap",
                        "left": previous["id"],
                        "right": current["id"],
                    }
                ],
            )

    count = len(proposed)
    removed_seconds = round(sum(float(item["duration"]) for item in proposed), 6)
    removed_fraction = removed_seconds / duration
    limit_blockers: list[dict[str, Any]] = []
    if count > int(GLOBAL_LIMITS["max_semantic_edits"]):
        limit_blockers.append(
            {
                "reason": "max_semantic_edits_exceeded",
                "actual": count,
                "limit": GLOBAL_LIMITS["max_semantic_edits"],
            }
        )
    if removed_seconds > float(GLOBAL_LIMITS["max_removed_seconds"]) + 1e-9:
        limit_blockers.append(
            {
                "reason": "max_removed_seconds_exceeded",
                "actual": removed_seconds,
                "limit": GLOBAL_LIMITS["max_removed_seconds"],
            }
        )
    if removed_fraction > float(GLOBAL_LIMITS["max_removed_fraction"]) + 1e-12:
        limit_blockers.append(
            {
                "reason": "max_removed_fraction_exceeded",
                "actual": round(removed_fraction, 9),
                "limit": GLOBAL_LIMITS["max_removed_fraction"],
            }
        )
    if limit_blockers:
        return _blocked(
            analysis_sha256=digest,
            source=source,
            mode=mode,
            status="blocked_global_limits",
            blockers=limit_blockers,
        )

    return {
        "schema_version": PROPOSAL_SCHEMA_VERSION,
        "record_type": PROPOSAL_RECORD_TYPE,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": PROPOSAL_READY_STATUS,
        "analysis_sha256": digest,
        "analysis_schema_version": analysis_schema,
        "source": source,
        "mode": mode,
        "limits": dict(GLOBAL_LIMITS),
        "blockers": [],
        "proposed_edits": proposed,
        "summary": {
            "proposed_edit_count": count,
            "removed_seconds": removed_seconds,
            "removed_fraction": round(removed_fraction, 9),
        },
        "requires_global_review": True,
        "globally_approved": False,
        "render_authorization": False,
        "executable": False,
        "auto_apply": False,
    }


def save_edit_plan_proposal(proposal: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
