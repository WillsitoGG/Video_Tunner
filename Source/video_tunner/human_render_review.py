from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HUMAN_RENDER_REVIEW_SCHEMA_VERSION = 1
HUMAN_RENDER_REVIEW_RECORD_TYPE = "semantic_render_human_review"
HUMAN_JOIN_DECISIONS = {"PASS", "FAIL"}


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _technical_review_snapshot(technical_report: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(technical_report, dict):
        raise ValueError("El technical verification report no es un objeto JSON.")
    if technical_report.get("schema_version") != 1:
        raise ValueError("Technical verification schema no soportado.")
    if technical_report.get("record_type") != "semantic_render_verification":
        raise ValueError("Technical verification record_type inválido.")
    if technical_report.get("status") != "technical_post_render_pass" or not technical_report.get("technical_pass"):
        raise ValueError("La revisión humana sólo puede registrar un render con gate técnico PASS.")
    if technical_report.get("blockers") not in ([], None):
        raise ValueError("El technical report contiene blockers.")
    if technical_report.get("auto_apply"):
        raise ValueError("El technical report no puede habilitar auto_apply.")

    output = technical_report.get("output")
    chain = technical_report.get("execution_chain")
    joins = technical_report.get("post_render_join_audits")
    if not isinstance(output, dict) or not isinstance(chain, dict) or not isinstance(joins, list) or not joins:
        raise ValueError("El technical report no contiene output/chain/joins revisables.")
    output_sha = str(output.get("sha256") or "").lower()
    plan_fingerprint = str(chain.get("plan_fingerprint") or "").lower()
    if not _valid_sha256(output_sha) or not _valid_sha256(plan_fingerprint):
        raise ValueError("El technical report no contiene provenance SHA/fingerprint válida.")

    join_snapshot: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, join in enumerate(joins, start=1):
        if not isinstance(join, dict):
            raise ValueError(f"Join técnico #{index} inválido.")
        join_id = str(join.get("id") or "")
        if not join_id or join_id in seen:
            raise ValueError("Los joins técnicos deben tener IDs únicos y no vacíos.")
        seen.add(join_id)
        if not join.get("technical_pass"):
            raise ValueError(f"El join {join_id} no superó el gate técnico.")
        join_snapshot.append(
            {
                "join_id": join_id,
                "edit_id": join.get("edit_id"),
                "candidate_id": join.get("candidate_id"),
                "output_join_seconds": join.get("output_join_seconds"),
                "technical_status": join.get("status"),
            }
        )

    return {
        "output_sha256": output_sha,
        "plan_fingerprint": plan_fingerprint,
        "join_count": len(join_snapshot),
        "joins": join_snapshot,
    }


def build_human_render_review(
    technical_report: dict[str, Any],
    join_decisions: list[dict[str, Any]],
    *,
    actor: str,
    reason: str,
    technical_report_sha256: str,
    created_utc: str | None = None,
) -> dict[str, Any]:
    """Record actual human listening decisions for every rendered semantic join.

    This function records evidence; it never substitutes automatic metrics for a
    human decision. A passing render review is still only one sample and cannot
    close the whole Phase 2E corpus by itself.
    """
    reviewer = actor.strip()
    overall_reason = reason.strip()
    report_sha = technical_report_sha256.strip().lower()
    if not reviewer:
        raise ValueError("actor humano es obligatorio.")
    if not overall_reason:
        raise ValueError("reason global de revisión humana es obligatorio.")
    if not _valid_sha256(report_sha):
        raise ValueError("technical_report_sha256 debe ser SHA-256 válido.")

    snapshot = _technical_review_snapshot(technical_report)
    expected_ids = [item["join_id"] for item in snapshot["joins"]]
    if not isinstance(join_decisions, list) or len(join_decisions) != len(expected_ids):
        raise ValueError("La revisión humana debe cubrir exactamente todos los joins técnicos.")

    decision_by_id: dict[str, dict[str, Any]] = {}
    for entry in join_decisions:
        if not isinstance(entry, dict):
            raise ValueError("Cada decisión humana debe ser un objeto.")
        join_id = str(entry.get("join_id") or "")
        decision = str(entry.get("decision") or "").strip().upper()
        rationale = str(entry.get("reason") or "").strip()
        if join_id not in expected_ids:
            raise ValueError(f"Join humano desconocido: {join_id}")
        if join_id in decision_by_id:
            raise ValueError(f"Join humano duplicado: {join_id}")
        if decision not in HUMAN_JOIN_DECISIONS:
            raise ValueError("decision humana debe ser PASS o FAIL.")
        if not rationale:
            raise ValueError("Cada join requiere reason humana auditable.")
        decision_by_id[join_id] = {
            "join_id": join_id,
            "decision": decision,
            "reason": rationale,
        }

    if set(decision_by_id) != set(expected_ids):
        raise ValueError("Faltan decisiones humanas para uno o más joins.")

    reviews: list[dict[str, Any]] = []
    for join in snapshot["joins"]:
        reviews.append({**join, **decision_by_id[join["join_id"]]})
    human_pass = all(item["decision"] == "PASS" for item in reviews)

    return {
        "schema_version": HUMAN_RENDER_REVIEW_SCHEMA_VERSION,
        "record_type": HUMAN_RENDER_REVIEW_RECORD_TYPE,
        "created_utc": created_utc or datetime.now(timezone.utc).isoformat(),
        "actor": reviewer,
        "reason": overall_reason,
        "technical_verification": {
            "sha256": report_sha,
            "output_sha256": snapshot["output_sha256"],
            "plan_fingerprint": snapshot["plan_fingerprint"],
        },
        "join_reviews": reviews,
        "status": "human_perceptual_pass" if human_pass else "human_perceptual_failed",
        "human_perceptual_pass": human_pass,
        "render_closeout_ready": human_pass,
        "phase2e_closeout_ready": False,
        "requires_phase2e_corpus_closeout": True,
        "auto_apply": False,
    }


def validate_human_render_review(
    technical_report: dict[str, Any],
    review: dict[str, Any],
    *,
    technical_report_sha256: str,
) -> dict[str, Any]:
    base = {
        "valid": False,
        "human_perceptual_pass": False,
        "render_closeout_ready": False,
        "phase2e_closeout_ready": False,
        "auto_apply": False,
    }
    if not isinstance(review, dict):
        return base | {"status": "invalid_record", "reason": "review_not_object"}
    if review.get("schema_version") != HUMAN_RENDER_REVIEW_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if review.get("record_type") != HUMAN_RENDER_REVIEW_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    if review.get("auto_apply") or review.get("phase2e_closeout_ready"):
        return base | {"status": "invalid_record", "reason": "forbidden_capability_claim"}
    if not review.get("requires_phase2e_corpus_closeout"):
        return base | {"status": "invalid_record", "reason": "missing_corpus_closeout_requirement"}
    if not str(review.get("actor") or "").strip() or not str(review.get("reason") or "").strip():
        return base | {"status": "invalid_record", "reason": "missing_human_audit_fields"}

    report_sha = technical_report_sha256.strip().lower()
    provenance = review.get("technical_verification")
    if not isinstance(provenance, dict):
        return base | {"status": "invalid_record", "reason": "missing_technical_provenance"}
    if provenance.get("sha256") != report_sha:
        return base | {"status": "stale_verification", "reason": "technical_report_sha256_changed"}

    try:
        snapshot = _technical_review_snapshot(technical_report)
    except ValueError as exc:
        return base | {"status": "stale_or_invalid_verification", "reason": str(exc)}
    if provenance.get("output_sha256") != snapshot["output_sha256"]:
        return base | {"status": "stale_verification", "reason": "output_sha256_changed"}
    if provenance.get("plan_fingerprint") != snapshot["plan_fingerprint"]:
        return base | {"status": "stale_verification", "reason": "plan_fingerprint_changed"}

    expected = {item["join_id"]: item for item in snapshot["joins"]}
    reviews = review.get("join_reviews")
    if not isinstance(reviews, list) or len(reviews) != len(expected):
        return base | {"status": "invalid_record", "reason": "join_review_coverage_mismatch"}

    seen: set[str] = set()
    all_pass = True
    for item in reviews:
        if not isinstance(item, dict):
            return base | {"status": "invalid_record", "reason": "join_review_not_object"}
        join_id = str(item.get("join_id") or "")
        if join_id not in expected or join_id in seen:
            return base | {"status": "invalid_record", "reason": "invalid_or_duplicate_join_id"}
        seen.add(join_id)
        contract = expected[join_id]
        for key in ("edit_id", "candidate_id", "output_join_seconds", "technical_status"):
            if item.get(key) != contract.get(key):
                return base | {"status": "stale_verification", "reason": f"join_snapshot_changed:{join_id}:{key}"}
        decision = str(item.get("decision") or "").upper()
        if decision not in HUMAN_JOIN_DECISIONS or not str(item.get("reason") or "").strip():
            return base | {"status": "invalid_record", "reason": "invalid_human_join_decision"}
        all_pass = all_pass and decision == "PASS"

    if seen != set(expected):
        return base | {"status": "invalid_record", "reason": "missing_join_review"}
    expected_status = "human_perceptual_pass" if all_pass else "human_perceptual_failed"
    if review.get("status") != expected_status:
        return base | {"status": "invalid_record", "reason": "review_status_mismatch"}
    if bool(review.get("human_perceptual_pass")) != all_pass:
        return base | {"status": "invalid_record", "reason": "human_pass_flag_mismatch"}
    if bool(review.get("render_closeout_ready")) != all_pass:
        return base | {"status": "invalid_record", "reason": "render_closeout_flag_mismatch"}

    return base | {
        "status": "valid_human_pass" if all_pass else "valid_human_fail",
        "reason": None,
        "valid": True,
        "human_perceptual_pass": all_pass,
        "render_closeout_ready": all_pass,
        "reviewed_join_count": len(expected),
    }


def save_human_render_review(review: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
