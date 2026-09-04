from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .acoustic_join import build_acoustic_join_assessments
from .eligibility import build_eligibility_assessments
from .human_acoustic_validation import build_human_join_evidence, _materialise_case


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def load_human_eligibility_inputs(
    expectation_path: str | Path,
    human_fixture_path: str | Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    expectations = json.loads(Path(expectation_path).read_text(encoding="utf-8"))
    human_fixture = json.loads(Path(human_fixture_path).read_text(encoding="utf-8"))
    expected_human_name = str(expectations.get("human_fixture") or "")
    if expected_human_name and Path(human_fixture_path).name != expected_human_name:
        raise ValueError(
            f"Human eligibility fixture mismatch: {Path(human_fixture_path).name} != {expected_human_name}"
        )
    return expectations, human_fixture


def _frozen_semantic_decisions(
    expectations: dict[str, Any], records_by_case: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for case in expectations["cases"]:
        raw = case.get("semantic_decision")
        if raw is None:
            continue
        case_id = str(case["id"])
        record = records_by_case.get(case_id)
        if record is None:
            raise ValueError(f"Unknown human eligibility case: {case_id}")
        candidate = record["candidate"]
        decision = dict(raw)
        decision["candidate_id"] = candidate["id"]
        decision["candidate_kind"] = candidate["kind"]
        decision["executable"] = False
        decision["auto_apply"] = False
        decisions.append(decision)
    return decisions


def validate_human_combined_eligibility(
    expectation_path: str | Path,
    human_fixture_path: str | Path,
    master_audio: str | Path,
) -> dict[str, Any]:
    expectations, human_fixture = load_human_eligibility_inputs(
        expectation_path, human_fixture_path
    )
    master = Path(master_audio)
    source = human_fixture["source"]
    if not master.is_file():
        raise FileNotFoundError(f"No existe el AMI master para eligibility humana: {master}")
    if master.stat().st_size != int(source["bytes"]):
        raise ValueError("AMI fixture bytes mismatch")
    if _sha256(master) != str(source["sha256"]).upper():
        raise ValueError("AMI fixture SHA-256 mismatch")

    context = build_human_join_evidence(human_fixture)
    records = context["records"]
    records_by_case = {str(record["case"]["id"]): record for record in records}

    expected_ids = [str(case["id"]) for case in expectations["cases"]]
    if set(expected_ids) != set(records_by_case):
        raise ValueError(
            "Human eligibility expectations must cover exactly the human acoustic fixture cases"
        )

    joins = [records_by_case[case_id]["join"] for case_id in expected_ids]
    acoustics = build_acoustic_join_assessments(master, joins)
    semantic_decisions = _frozen_semantic_decisions(expectations, records_by_case)
    acoustic_by_join = {
        str(item.get("join_assessment_id")): item for item in acoustics
    }
    semantic_by_candidate = {
        str(item.get("candidate_id")): item for item in semantic_decisions
    }

    results: list[dict[str, Any]] = []
    failures: list[str] = []
    for expected in expectations["cases"]:
        case_id = str(expected["id"])
        record = records_by_case[case_id]
        candidate = record["candidate"]
        join = record["join"]
        acoustic = acoustic_by_join[str(join["id"])]
        transcript, _ = _materialise_case(record["case"])
        semantic = semantic_by_candidate.get(str(candidate["id"]))
        assessments = build_eligibility_assessments(
            transcript,
            [candidate],
            semantic_decisions=[semantic] if semantic else [],
            correction_scopes=record["correction_scopes"],
            filler_assessments=[],
            join_assessments=[join],
            acoustic_join_assessments=[acoustic],
        )
        if len(assessments) != 1:
            failures.append(f"{case_id}: eligibility record count={len(assessments)}")
            continue
        item = assessments[0]
        expected_status = str(expected["expected_eligibility_status"])
        expected_promotion = bool(expected["expected_future_promotion_candidate"])
        if str(item.get("status")) != expected_status:
            failures.append(
                f"{case_id}: eligibility status {item.get('status')} != {expected_status}"
            )
        if bool(item.get("future_promotion_candidate")) != expected_promotion:
            failures.append(f"{case_id}: future_promotion_candidate mismatch")
        if item.get("safe_for_cut") or item.get("executable") or item.get("auto_apply"):
            failures.append(f"{case_id}: eligibility violated safety contract")

        results.append(
            {
                "id": case_id,
                "source_type": record["case"].get("source_type"),
                "join_status": join.get("status"),
                "acoustic_status": acoustic.get("status"),
                "measurement_available": bool(acoustic.get("measurement_available")),
                "semantic_decision": semantic.get("decision") if semantic else None,
                "correction_scope_status": (
                    record["correction_scopes"][0].get("status")
                    if record["correction_scopes"]
                    else None
                ),
                "eligibility_status": item.get("status"),
                "removed_text_valid": bool(
                    (item.get("removed_text_validation") or {}).get("valid")
                ),
                "removed_text_reason": (
                    item.get("removed_text_validation") or {}
                ).get("reason"),
                "future_promotion_candidate": bool(
                    item.get("future_promotion_candidate")
                ),
                "safe_for_cut": bool(item.get("safe_for_cut")),
                "executable": bool(item.get("executable")),
                "auto_apply": bool(item.get("auto_apply")),
            }
        )

    return {
        "schema_version": 1,
        "source": source,
        "semantic_reference": expectations["semantic_reference"],
        "cases": len(results),
        "failures": len(failures),
        "foundation_guards_pass": sum(
            1 for item in results if item["eligibility_status"] == "foundation_guards_pass"
        ),
        "blocked": sum(
            1 for item in results if item["eligibility_status"] != "foundation_guards_pass"
        ),
        "safe_for_cut": sum(1 for item in results if item["safe_for_cut"]),
        "executable": sum(1 for item in results if item["executable"]),
        "auto_apply": sum(1 for item in results if item["auto_apply"]),
        "automatic_edits": 0,
        "results": results,
        "failure_messages": failures,
    }


def human_eligibility_gate(summary: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "all_cases_evaluated": int(summary["cases"]) >= 3,
        "human_foundation_control_exists": int(summary["foundation_guards_pass"]) >= 1,
        "human_blockers_preserved": int(summary["blocked"]) >= 2,
        "no_contract_failures": int(summary["failures"]) == 0,
        "non_executable": int(summary["safe_for_cut"]) == 0
        and int(summary["executable"]) == 0
        and int(summary["auto_apply"]) == 0
        and int(summary["automatic_edits"]) == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate combined eligibility on frozen real AMI evidence."
    )
    parser.add_argument("--expectations", required=True)
    parser.add_argument("--human-fixture", required=True)
    parser.add_argument("--master-audio", required=True)
    args = parser.parse_args()

    summary = validate_human_combined_eligibility(
        args.expectations,
        args.human_fixture,
        args.master_audio,
    )
    gate = human_eligibility_gate(summary)
    print(
        "HUMAN_ELIGIBILITY_SUMMARY="
        + json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
    )
    print("HUMAN_ELIGIBILITY_GATE=" + ("PASS" if gate["passed"] else "FAIL"))
    print(
        "HUMAN_ELIGIBILITY_CHECKS="
        + json.dumps(gate["checks"], separators=(",", ":"))
    )
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
