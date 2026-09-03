from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .acoustic_join import build_acoustic_join_assessments
from .correction_scope import build_correction_scopes
from .join_safety import build_join_assessments
from .transcription import TranscriptResult, TranscriptSegment, WordTiming

MEASURED_ACOUSTIC_STATUSES = {
    "low_energy_boundary_context",
    "level_discontinuity_risk",
    "waveform_discontinuity_risk",
    "combined_discontinuity_risk",
    "acoustic_context_only",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _materialise_case(case: dict[str, Any]) -> tuple[TranscriptResult, dict[str, Any]]:
    offset = float(case["source_window_start"])
    words = tuple(
        WordTiming(
            str(item["text"]),
            offset + float(item["start"]),
            offset + float(item["end"]),
            None if item.get("probability") is None else float(item["probability"]),
        )
        for item in case["words"]
    )
    if not words:
        raise ValueError(f"Human acoustic case {case.get('id')} has no words")

    transcript = TranscriptResult(
        language="en",
        language_probability=0.99,
        model="large-v3-turbo@run-33755013415",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=" ".join(word.text for word in words),
                start=words[0].start,
                end=words[-1].end,
                words=words,
            ),
        ),
    )

    raw_candidate = case["candidate"]
    start = offset + float(raw_candidate["start"])
    end = offset + float(raw_candidate["end"])
    candidate: dict[str, Any] = {
        "id": f"human-{case['id']}",
        "kind": str(raw_candidate["kind"]),
        "start": start,
        "end": end,
        "duration": round(end - start, 6),
        "reason": str(raw_candidate.get("reason") or case.get("purpose") or "human acoustic evidence"),
        "confidence": None,
        "decision": "undecided",
        "auto_apply": False,
    }
    if "word_start_index" in raw_candidate:
        candidate["evidence"] = {
            "removed_text": str(raw_candidate["removed_text"]),
            "word_start_index": int(raw_candidate["word_start_index"]),
            "word_end_index_exclusive": int(raw_candidate["word_end_index_exclusive"]),
            "requires_semantic_review": True,
            "span_safe_for_auto_apply": False,
            "source": "frozen-large-v3-turbo-run-33755013415",
        }
    return transcript, candidate


def build_human_join_evidence(fixture: dict[str, Any]) -> dict[str, Any]:
    """Rebuild join-context evidence from frozen real-ASR word timings."""
    records: list[dict[str, Any]] = []
    for index, case in enumerate(fixture["cases"], start=1):
        transcript, candidate = _materialise_case(case)
        scopes = build_correction_scopes(transcript, [candidate])
        join = build_join_assessments(
            transcript,
            [candidate],
            correction_scopes=scopes,
            filler_assessments=[],
        )[0]
        join["id"] = f"human-join-assessment-{index:04d}"
        records.append(
            {
                "case": case,
                "candidate": candidate,
                "correction_scopes": scopes,
                "join": join,
            }
        )
    return {"records": records}


def validate_human_acoustic_evidence(
    fixture_path: str | Path,
    master_audio: str | Path,
) -> dict[str, Any]:
    fixture_file = Path(fixture_path)
    master = Path(master_audio)
    fixture = json.loads(fixture_file.read_text(encoding="utf-8"))
    source = fixture["source"]

    if not master.is_file():
        raise FileNotFoundError(f"No existe el AMI master para validación acústica: {master}")
    actual_bytes = master.stat().st_size
    actual_sha = _sha256(master)
    if actual_bytes != int(source["bytes"]):
        raise ValueError(f"AMI fixture bytes mismatch: {actual_bytes} != {source['bytes']}")
    if actual_sha != str(source["sha256"]).upper():
        raise ValueError(f"AMI fixture SHA-256 mismatch: {actual_sha}")

    context = build_human_join_evidence(fixture)
    joins = [record["join"] for record in context["records"]]
    acoustic = build_acoustic_join_assessments(master, joins)
    acoustic_by_join = {item["join_assessment_id"]: item for item in acoustic}

    failures: list[str] = []
    results: list[dict[str, Any]] = []
    for record in context["records"]:
        case = record["case"]
        join = record["join"]
        item = acoustic_by_join[join["id"]]
        case_id = str(case["id"])
        expected_join = str(case["expected_join_status"])
        if join.get("status") != expected_join:
            failures.append(
                f"{case_id}: join status {join.get('status')} != expected {expected_join}"
            )

        expected_scope = case.get("expected_scope_status")
        scopes = record["correction_scopes"]
        if expected_scope is not None:
            actual_scope = scopes[0]["status"] if scopes else None
            if actual_scope != expected_scope:
                failures.append(
                    f"{case_id}: correction scope {actual_scope} != expected {expected_scope}"
                )

        expected_acoustic = case.get("expected_acoustic_status")
        contract = case.get("expected_acoustic_contract")
        if expected_acoustic is not None and item.get("status") != expected_acoustic:
            failures.append(
                f"{case_id}: acoustic status {item.get('status')} != expected {expected_acoustic}"
            )
        if contract == "measured":
            if not item.get("measurement_available"):
                failures.append(f"{case_id}: expected real acoustic measurement")
            if item.get("status") not in MEASURED_ACOUSTIC_STATUSES:
                failures.append(
                    f"{case_id}: measured control produced non-measured status {item.get('status')}"
                )

        if item.get("safe_for_cut") or item.get("executable") or item.get("auto_apply"):
            failures.append(f"{case_id}: acoustic evidence violated non-executable safety contract")
        if join.get("safe_for_cut") or join.get("executable") or join.get("auto_apply"):
            failures.append(f"{case_id}: join evidence violated non-executable safety contract")

        results.append(
            {
                "id": case_id,
                "source_type": case.get("source_type"),
                "expected_join_status": expected_join,
                "join_status": join.get("status"),
                "correction_scope_status": (
                    scopes[0]["status"] if scopes else None
                ),
                "acoustic_status": item.get("status"),
                "measurement_available": bool(item.get("measurement_available")),
                "metrics": item.get("metrics"),
                "safe_for_cut": bool(item.get("safe_for_cut")),
                "executable": bool(item.get("executable")),
                "auto_apply": bool(item.get("auto_apply")),
            }
        )

    summary = {
        "schema_version": 1,
        "source": source,
        "asr_reference": fixture["asr_reference"],
        "cases": len(results),
        "failures": len(failures),
        "measured_cases": sum(1 for item in results if item["measurement_available"]),
        "blocked_cases": sum(1 for item in results if item["acoustic_status"] == "blocked_by_context"),
        "automatic_edits": 0,
        "executable": 0,
        "auto_apply": 0,
        "results": results,
        "failure_messages": failures,
    }
    return summary


def human_acoustic_gate(summary: dict[str, Any]) -> dict[str, Any]:
    checks = {
        "all_cases_evaluated": int(summary["cases"]) >= 3,
        "at_least_one_real_measurement": int(summary["measured_cases"]) >= 1,
        "context_blocks_preserved": int(summary["blocked_cases"]) >= 2,
        "no_contract_failures": int(summary["failures"]) == 0,
        "non_executable": int(summary["executable"]) == 0
        and int(summary["auto_apply"]) == 0
        and int(summary["automatic_edits"]) == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate acoustic join evidence on real AMI human audio.")
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--master-audio", required=True)
    args = parser.parse_args()

    summary = validate_human_acoustic_evidence(args.fixture, args.master_audio)
    gate = human_acoustic_gate(summary)
    print("HUMAN_ACOUSTIC_SUMMARY=" + json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    print("HUMAN_ACOUSTIC_GATE=" + ("PASS" if gate["passed"] else "FAIL"))
    print("HUMAN_ACOUSTIC_CHECKS=" + json.dumps(gate["checks"], separators=(",", ":")))
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
