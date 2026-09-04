from __future__ import annotations

from pathlib import Path
from typing import Any

from .approval import sha256_path
from .render import render_from_plan
from .semantic_edit_plan import validate_semantic_edit_plan


def validate_semantic_render_request(
    source: str | Path,
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    plan: dict[str, Any],
    *,
    analysis_sha256: str,
    proposal_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    """Revalidate the full semantic execution chain immediately before FFmpeg."""
    base = {
        "valid": False,
        "render_authorized": False,
        "auto_apply": False,
    }
    plan_validation = validate_semantic_edit_plan(
        analysis,
        proposal,
        authorization,
        plan,
        analysis_sha256=analysis_sha256,
        proposal_sha256=proposal_sha256,
        authorization_sha256=authorization_sha256,
    )
    if plan_validation.get("status") != "valid_semantic_edit_plan":
        return base | {
            "status": "blocked_invalid_semantic_plan",
            "reason": plan_validation.get("reason"),
            "plan_status": plan_validation.get("status"),
        }

    source_path = Path(source)
    if not source_path.is_file():
        return base | {"status": "blocked_source_mismatch", "reason": "source_not_found"}
    source_sha = sha256_path(source_path)

    analysis_source = analysis.get("source")
    proposal_source = proposal.get("source")
    plan_source = plan.get("source")
    expected_hashes = []
    for label, block in (
        ("analysis", analysis_source),
        ("proposal", proposal_source),
        ("plan", plan_source),
    ):
        if not isinstance(block, dict):
            return base | {
                "status": "blocked_source_mismatch",
                "reason": f"{label}_source_missing",
            }
        expected = str(block.get("sha256") or "").lower()
        expected_hashes.append((label, expected))

    mismatches = [label for label, expected in expected_hashes if expected != source_sha]
    if mismatches:
        return base | {
            "status": "blocked_source_mismatch",
            "reason": "source_sha256_changed",
            "mismatched_layers": mismatches,
            "actual_source_sha256": source_sha,
        }

    if not bool(authorization.get("semantic_render_authorization")):
        return base | {
            "status": "blocked_execution_authorization",
            "reason": "semantic_render_authorization_not_present",
        }

    return base | {
        "status": "valid_semantic_render_request",
        "reason": None,
        "valid": True,
        "render_authorized": True,
        "source_sha256": source_sha,
        "plan_fingerprint": plan_validation.get("plan_fingerprint"),
        "edit_count": plan_validation.get("edit_count"),
    }


def render_semantic_plan(
    source: str | Path,
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    plan: dict[str, Any],
    destination: str | Path,
    *,
    analysis_sha256: str,
    proposal_sha256: str,
    authorization_sha256: str,
) -> Path:
    validation = validate_semantic_render_request(
        source,
        analysis,
        proposal,
        authorization,
        plan,
        analysis_sha256=analysis_sha256,
        proposal_sha256=proposal_sha256,
        authorization_sha256=authorization_sha256,
    )
    if validation.get("status") != "valid_semantic_render_request":
        raise ValueError(
            "Semantic render gate bloqueado: "
            f"{validation.get('status')} ({validation.get('reason')})"
        )
    return render_from_plan(
        source,
        plan,
        destination,
        semantic_gate_authorized=True,
    )
