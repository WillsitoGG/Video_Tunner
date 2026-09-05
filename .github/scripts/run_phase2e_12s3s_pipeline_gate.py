from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import unicodedata
import wave
from pathlib import Path
from typing import Any

from video_tunner.analysis_pipeline import analyze_spoken_video
from video_tunner.transcription import (
    CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    build_transcription_chunk_windows,
)
from video_tunner.transcription_profiles import (
    CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
    CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
)


TIMING_TOLERANCE_SECONDS = 0.75
ACOUSTIC_GATE_PASS_STATUSES = {
    "acoustic_context_only",
    "low_energy_boundary_context",
}


def _normalise_phrase(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text.lower())
    without_marks = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    tokens = []
    for raw in without_marks.split():
        token = re.sub(r"[^a-z0-9]+", "", raw)
        if token:
            tokens.append(token)
    return " ".join(tokens)


def _run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"STDOUT:\n{completed.stdout}\nSTDERR:\n{completed.stderr}"
        )


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def _source_env_name(source_id: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", source_id.upper())
    return f"AMI_CLOSEOUT_{compact}_WAV"


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _linked_record(
    records: list[dict[str, Any]], candidate_id: str
) -> dict[str, Any] | None:
    matches = [
        item
        for item in records
        if str(item.get("candidate_id") or "") == candidate_id
    ]
    return matches[0] if len(matches) == 1 else None


def _acoustic_for_join(
    records: list[dict[str, Any]], join_id: str
) -> dict[str, Any] | None:
    matches = [
        item
        for item in records
        if str(item.get("join_assessment_id") or "") == join_id
    ]
    return matches[0] if len(matches) == 1 else None


def _safety_violations(analysis: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    if int((analysis.get("summary") or {}).get("automatic_edits") or 0) != 0:
        violations.append("summary.automatic_edits_nonzero")

    array_rules = {
        "candidates": ("auto_apply",),
        "correction_scopes": ("safe_for_cut", "executable", "auto_apply"),
        "filler_assessments": ("safe_for_cut", "executable", "auto_apply"),
        "semantic_decisions": ("executable", "auto_apply"),
        "join_assessments": ("safe_for_cut", "executable", "auto_apply"),
        "acoustic_join_assessments": ("safe_for_cut", "executable", "auto_apply"),
        "eligibility_assessments": ("safe_for_cut", "executable", "auto_apply"),
        "promotion_assessments": (
            "approved",
            "safe_for_cut",
            "executable",
            "auto_apply",
        ),
    }
    for array_name, fields in array_rules.items():
        for index, item in enumerate(analysis.get(array_name) or []):
            for field in fields:
                if bool(item.get(field)):
                    violations.append(f"{array_name}[{index}].{field}=true")
            if array_name == "promotion_assessments" and item.get("edit") is not None:
                violations.append(f"{array_name}[{index}].edit_present")
    return violations


def _evaluate_case(
    case: dict[str, Any],
    *,
    case_root: Path,
    ffmpeg: Path,
) -> dict[str, Any]:
    case_id = str(case["id"])
    source_id = str(case["audio_source_id"])
    env_name = _source_env_name(source_id)
    source_value = os.environ.get(env_name)
    if not source_value or not Path(source_value).is_file():
        raise RuntimeError(f"Missing AMI source for {case_id}: {env_name}")
    source_wav = Path(source_value)

    root = case_root / case_id
    output = root / "Analysis"
    root.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    clip_wav = root / f"{case_id}.wav"
    input_video = root / f"{case_id}.mp4"

    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])
    _run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            str(render_start),
            "-t",
            str(render_duration),
            "-i",
            str(source_wav),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(clip_wav),
        ]
    )
    duration = _wav_duration(clip_wav)
    if duration < 40.0:
        raise RuntimeError(f"Render context too short for {case_id}: {duration:.3f}s")

    _run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=320x240:r=25:d={duration:.6f}",
            "-i",
            str(clip_wav),
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(input_video),
        ]
    )

    result = analyze_spoken_video(
        input_video,
        output,
        mode="conservative",
        model_name="large-v3-turbo",
        language="en",
        device="cpu",
        compute_type="int8",
        transcription_strategy=CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
    )
    if result.get("status") != "analyzed":
        raise RuntimeError(f"Analyze did not complete for {case_id}: {result}")

    transcript = _load_json(result["transcript_json"])
    analysis = _load_json(result["analysis"])
    strategy = transcript.get("strategy") or {}
    expected_chunk_count = len(
        build_transcription_chunk_windows(
            duration,
            window_seconds=CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
            hop_seconds=CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
        )
    )
    strategy_ok = (
        int(transcript.get("schema_version") or 0) >= 2
        and strategy.get("name") == CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY
        and abs(
            float(strategy.get("chunk_window_seconds"))
            - CHUNKED_TRANSCRIPTION_WINDOW_SECONDS
        )
        <= 1e-9
        and abs(
            float(strategy.get("chunk_hop_seconds"))
            - CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS
        )
        <= 1e-9
        and int(strategy.get("chunk_count") or 0) == expected_chunk_count
    )

    expected_text = _normalise_phrase(str(case["reparandum_text"]))
    promotion_matches = []
    for promotion in analysis.get("promotion_assessments") or []:
        target = promotion.get("target_preview") or {}
        if (
            promotion.get("status") == "eligible_for_promotion_review"
            and promotion.get("candidate_kind") == case.get("expected_candidate_kind")
            and _normalise_phrase(target.get("text")) == expected_text
        ):
            promotion_matches.append(promotion)

    promotion = promotion_matches[0] if len(promotion_matches) == 1 else None
    candidate = None
    decision = None
    join = None
    acoustic = None
    eligibility = None
    target = None
    start_delta = None
    end_delta = None
    timing_ok = False
    layer_chain_ok = False

    if promotion is not None:
        candidate_id = str(promotion.get("candidate_id") or "")
        candidate = _linked_record(analysis.get("candidates") or [], candidate_id)
        decision = _linked_record(
            analysis.get("semantic_decisions") or [], candidate_id
        )
        join = _linked_record(analysis.get("join_assessments") or [], candidate_id)
        eligibility = _linked_record(
            analysis.get("eligibility_assessments") or [], candidate_id
        )
        if join is not None:
            acoustic = _acoustic_for_join(
                analysis.get("acoustic_join_assessments") or [],
                str(join.get("id") or ""),
            )
        target = promotion.get("target_preview") or {}
        manual_local_start = float(case["reparandum_start"]) - render_start
        manual_local_end = float(case["reparandum_end"]) - render_start
        if target.get("start") is not None and target.get("end") is not None:
            start_delta = abs(float(target["start"]) - manual_local_start)
            end_delta = abs(float(target["end"]) - manual_local_end)
            timing_ok = (
                start_delta <= TIMING_TOLERANCE_SECONDS
                and end_delta <= TIMING_TOLERANCE_SECONDS
            )
        layer_chain_ok = bool(
            candidate
            and candidate.get("kind") == case.get("expected_candidate_kind")
            and _normalise_phrase(
                (candidate.get("evidence") or {}).get("removed_text")
            )
            == expected_text
            and decision
            and decision.get("decision") == "PROPOSED_CUT"
            and decision.get("guard_status") == "pass"
            and join
            and join.get("status") == "join_context_only"
            and acoustic
            and acoustic.get("status") in ACOUSTIC_GATE_PASS_STATUSES
            and bool(acoustic.get("measurement_available"))
            and eligibility
            and eligibility.get("status") == "foundation_guards_pass"
            and bool(
                (eligibility.get("removed_text_validation") or {}).get("valid")
            )
            and bool(eligibility.get("future_promotion_candidate"))
            and bool(promotion.get("promotion_review_candidate"))
            and promotion.get("approval_state") == "required"
        )

    safety = _safety_violations(analysis)
    case_pass = bool(
        strategy_ok
        and len(promotion_matches) == 1
        and timing_ok
        and layer_chain_ok
        and not safety
    )

    record = {
        "id": case_id,
        "audio_source_id": source_id,
        "human_label": case.get("human_label"),
        "expected_removed_text": case.get("reparandum_text"),
        "render_clip_start": render_start,
        "render_clip_duration": render_duration,
        "actual_clip_duration": round(duration, 6),
        "expected_chunk_count": expected_chunk_count,
        "transcription_strategy": strategy,
        "strategy_ok": strategy_ok,
        "promotion_match_count": len(promotion_matches),
        "promotion_assessment_id": None if promotion is None else promotion.get("id"),
        "candidate_id": None if promotion is None else promotion.get("candidate_id"),
        "semantic_decision": None if decision is None else decision.get("decision"),
        "semantic_guard_status": None
        if decision is None
        else decision.get("guard_status"),
        "join_status": None if join is None else join.get("status"),
        "acoustic_status": None if acoustic is None else acoustic.get("status"),
        "eligibility_status": None
        if eligibility is None
        else eligibility.get("status"),
        "target_text": None if target is None else target.get("text"),
        "target_start": None if target is None else target.get("start"),
        "target_end": None if target is None else target.get("end"),
        "start_delta_seconds": start_delta,
        "end_delta_seconds": end_delta,
        "timing_ok": timing_ok,
        "layer_chain_ok": layer_chain_ok,
        "safety_violations": safety,
        "pass": case_pass,
    }
    print(
        f"PHASE2E_12S3S_PIPELINE_CASE={case_id} "
        f"PASS={int(case_pass)} PROMOTIONS={len(promotion_matches)} "
        f"STRATEGY_OK={int(strategy_ok)} TIMING_OK={int(timing_ok)} "
        f"CHAIN_OK={int(layer_chain_ok)} SAFETY={len(safety)}"
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    ffmpeg = Path(args.ffmpeg)
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.json"
    case_root = output_root / "Cases"
    case_root.mkdir(parents=True, exist_ok=True)

    spec = _load_json(fixture_path)
    results: list[dict[str, Any]] = []
    hard_failures: list[str] = []
    for case in spec.get("cases") or []:
        try:
            results.append(
                _evaluate_case(case, case_root=case_root, ffmpeg=ffmpeg)
            )
        except Exception as exc:
            case_id = str(case.get("id") or "unknown")
            message = f"{case_id}: {type(exc).__name__}: {exc}"
            hard_failures.append(message)
            results.append(
                {
                    "id": case_id,
                    "audio_source_id": case.get("audio_source_id"),
                    "pass": False,
                    "hard_failure": message,
                }
            )
            print(f"PHASE2E_12S3S_PIPELINE_HARD_FAILURE={message}")

    pass_count = sum(1 for item in results if item.get("pass"))
    source_ids = {
        str(item.get("audio_source_id"))
        for item in results
        if item.get("audio_source_id")
    }
    gate_pass = (
        len(results) == 3
        and pass_count == 3
        and len(source_ids) >= 2
        and not hard_failures
    )
    manifest = {
        "schema_version": 1,
        "phase": "2E deterministic 12s-3s full pipeline gate",
        "source_fixture": fixture_path.name,
        "transcription_strategy": CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
        "grid_origin": "local_input_t0",
        "window_seconds": CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
        "hop_seconds": CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
        "timing_tolerance_seconds": TIMING_TOLERANCE_SECONDS,
        "acoustic_gate_pass_statuses": sorted(ACOUSTIC_GATE_PASS_STATUSES),
        "required_cases": 3,
        "required_distinct_sources": 2,
        "cases": results,
        "pass_count": pass_count,
        "distinct_source_count": len(source_ids),
        "hard_failures": hard_failures,
        "gate": "PASS" if gate_pass else "FAIL",
        "product_default_changed": False,
        "cli_strategy_exposed": False,
        "detector_threshold_changed": False,
        "downstream_guard_changed": True,
        "downstream_guard_change_scope": "chunked exact-adjacent possible_repetition segment boundary only",
        "approval_created": False,
        "execution_authorization_created": False,
        "render_performed": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"PHASE2E_12S3S_PIPELINE_PASS_COUNT={pass_count}/3")
    print(f"PHASE2E_12S3S_PIPELINE_DISTINCT_SOURCES={len(source_ids)}")
    print(f"PHASE2E_12S3S_PIPELINE_GATE={manifest['gate']}")
    print(f"PHASE2E_12S3S_PIPELINE_MANIFEST={manifest_path}")
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
