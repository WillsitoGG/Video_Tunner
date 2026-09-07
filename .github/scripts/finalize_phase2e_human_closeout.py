from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from video_tunner.approval import load_json_object, sha256_path
from video_tunner.human_render_review import build_human_render_review, save_human_render_review
from video_tunner.phase2e_closeout import build_phase2e_closeout_decision

DECISIONS_SCHEMA_VERSION = 1
DECISIONS_RECORD_TYPE = "phase2e_human_render_decisions"
FINALIZATION_SCHEMA_VERSION = 1
FINALIZATION_RECORD_TYPE = "phase2e_human_closeout_finalization"


def _write_json(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _load_decisions(path: Path, expected_case_ids: list[str]) -> dict[str, Any]:
    payload = load_json_object(path)
    if payload.get("schema_version") != DECISIONS_SCHEMA_VERSION:
        raise ValueError("Human decisions schema no soportado.")
    if payload.get("record_type") != DECISIONS_RECORD_TYPE:
        raise ValueError("Human decisions record_type inválido.")
    actor = str(payload.get("actor") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    if not actor or not reason:
        raise ValueError("Human decisions requiere actor y reason global no vacíos.")

    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Human decisions cases debe ser una lista.")
    by_id: dict[str, dict[str, Any]] = {}
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Cada human decision case debe ser un objeto.")
        case_id = str(case.get("id") or "")
        if not case_id or case_id in by_id:
            raise ValueError("Human decisions contiene case id vacío o duplicado.")
        join_decisions = case.get("join_decisions")
        if not isinstance(join_decisions, list):
            raise ValueError(f"{case_id}: join_decisions debe ser una lista.")
        by_id[case_id] = case

    if set(by_id) != set(expected_case_ids):
        missing = sorted(set(expected_case_ids) - set(by_id))
        extra = sorted(set(by_id) - set(expected_case_ids))
        raise ValueError(f"Human decisions no coincide con el corpus bloqueado; missing={missing}, extra={extra}.")
    return payload | {"_cases_by_id": by_id}


def finalize(bundle_dir: Path, decisions_path: Path, output_dir: Path) -> dict[str, Any]:
    bundle_dir = bundle_dir.resolve()
    decisions_path = decisions_path.resolve()
    output_dir = output_dir.resolve()

    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"No existe manifest.json en bundle: {manifest_path}")
    manifest = load_json_object(manifest_path)
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Bundle manifest no contiene cases válidos.")
    case_ids = [str(case.get("id") or "") for case in cases]
    if "" in case_ids or len(set(case_ids)) != len(case_ids):
        raise ValueError("Bundle manifest contiene case ids vacíos o duplicados.")

    decisions = _load_decisions(decisions_path, case_ids)
    actor = str(decisions["actor"]).strip()
    global_reason = str(decisions["reason"]).strip()
    decisions_by_id: dict[str, dict[str, Any]] = decisions["_cases_by_id"]

    reports: dict[str, dict[str, Any]] = {}
    reviews: dict[str, dict[str, Any]] = {}
    report_shas: dict[str, str] = {}
    review_shas: dict[str, str] = {}

    for case in cases:
        case_id = str(case["id"])
        case_dir = bundle_dir / case_id
        report_path = case_dir / "technical_verification.json"
        if not report_path.is_file():
            raise FileNotFoundError(f"{case_id}: falta technical_verification.json")
        report_sha = sha256_path(report_path)
        expected_report_sha = str(case.get("technical_report_sha256") or "").lower()
        if report_sha != expected_report_sha:
            raise ValueError(
                f"{case_id}: technical report SHA no coincide con manifest; "
                f"expected={expected_report_sha}, actual={report_sha}."
            )

        report = load_json_object(report_path)
        case_input = decisions_by_id[case_id]
        case_reason = str(case_input.get("reason") or global_reason).strip()
        if not case_reason:
            raise ValueError(f"{case_id}: reason humana no puede estar vacía.")
        review = build_human_render_review(
            report,
            case_input["join_decisions"],
            actor=actor,
            reason=case_reason,
            technical_report_sha256=report_sha,
        )
        review_path = save_human_render_review(
            review,
            output_dir / case_id / "human_render_review.json",
        )
        reports[case_id] = report
        reviews[case_id] = review
        report_shas[case_id] = report_sha
        review_shas[case_id] = sha256_path(review_path)

    closeout = build_phase2e_closeout_decision(
        manifest,
        reports,
        reviews,
        technical_report_sha256=report_shas,
    )
    closeout_path = _write_json(closeout, output_dir / "phase2e_closeout_decision.json")
    finalization = {
        "schema_version": FINALIZATION_SCHEMA_VERSION,
        "record_type": FINALIZATION_RECORD_TYPE,
        "source_bundle": {
            "manifest_sha256": sha256_path(manifest_path),
            "human_decisions_sha256": sha256_path(decisions_path),
        },
        "case_review_sha256": review_shas,
        "closeout_decision_sha256": sha256_path(closeout_path),
        "status": closeout.get("status"),
        "phase2e_closeout_ready": bool(closeout.get("phase2e_closeout_ready")),
        "auto_apply": False,
    }
    _write_json(finalization, output_dir / "finalization_manifest.json")
    return finalization


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finalize Phase 2E.5 from an immutable technical bundle plus explicit human listening decisions."
    )
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    result = finalize(Path(args.bundle_dir), Path(args.decisions), Path(args.output_dir))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    status = result.get("status")
    if status == "CLOSE_OUT_READY":
        return 0
    if status == "INSUFFICIENT_JOIN_QUALITY":
        return 3
    return 4


if __name__ == "__main__":
    raise SystemExit(main())
