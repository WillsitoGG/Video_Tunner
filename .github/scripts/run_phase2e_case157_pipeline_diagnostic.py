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
from video_tunner.transcription_profiles import CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY

CASE_ID = "ami-es2002b-d-repeat-157"
FOCUS_PADDING_SECONDS = 3.0
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _normalise_phrase(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(token for raw in asciiish.split() if (token := _TOKEN_RE.sub("", raw)))


def _source_env_name(source_id: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", source_id.upper())
    return f"AMI_CLOSEOUT_{compact}_WAV"


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


def _load_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _by_candidate(records: list[dict[str, Any]], candidate_id: str) -> list[dict[str, Any]]:
    return [item for item in records if str(item.get("candidate_id") or "") == candidate_id]


def _acoustic_for_join(records: list[dict[str, Any]], join_id: str) -> list[dict[str, Any]]:
    return [item for item in records if str(item.get("join_assessment_id") or "") == join_id]


def _excerpt_words(transcript: dict[str, Any], start: float, end: float) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for segment in transcript.get("segments") or []:
        for word in segment.get("words") or []:
            try:
                word_start = float(word["start"])
                word_end = float(word["end"])
            except (KeyError, TypeError, ValueError):
                continue
            if word_end < start or word_start > end:
                continue
            words.append(
                {
                    "text": str(word.get("text") or ""),
                    "start": round(word_start, 6),
                    "end": round(word_end, 6),
                }
            )
    return sorted(words, key=lambda item: (item["start"], item["end"], item["text"]))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture = _load_json(args.fixture)
    case = next(item for item in fixture.get("cases") or [] if item.get("id") == CASE_ID)
    source_id = str(case["audio_source_id"])
    source_raw = os.environ.get(_source_env_name(source_id))
    if not source_raw or not Path(source_raw).is_file():
        raise RuntimeError(f"Missing AMI source for {CASE_ID}: {source_id}")

    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=True)
    clip_wav = root / "source_clip.wav"
    input_video = root / "case157.mp4"
    analysis_root = root / "Analysis"
    ffmpeg = Path(args.ffmpeg)
    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])

    _run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(render_start), "-t", str(render_duration), "-i", str(source_raw),
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(clip_wav),
    ])
    duration = _wav_duration(clip_wav)
    _run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=320x240:r=25:d={duration:.6f}",
        "-i", str(clip_wav), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", str(input_video),
    ])

    result = analyze_spoken_video(
        input_video,
        analysis_root,
        mode="conservative",
        model_name="large-v3-turbo",
        language="en",
        device="cpu",
        compute_type="int8",
        transcription_strategy=CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
    )
    if result.get("status") != "analyzed":
        raise RuntimeError(f"Analyze did not complete: {result}")

    transcript = _load_json(result["transcript_json"])
    analysis = _load_json(result["analysis"])
    expected = _normalise_phrase(str(case["reparandum_text"]))
    manual_start = float(case["reparandum_start"]) - render_start
    manual_end = float(case["reparandum_end"]) - render_start

    candidate_records: list[dict[str, Any]] = []
    exact_candidate_ids: list[str] = []
    for candidate in analysis.get("candidates") or []:
        if candidate.get("kind") != case.get("expected_candidate_kind"):
            continue
        candidate_id = str(candidate.get("id") or "")
        removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
        text_match = _normalise_phrase(removed) == expected
        try:
            candidate_start = float(candidate.get("start"))
            candidate_end = float(candidate.get("end"))
            overlaps_manual = candidate_end >= manual_start - 1.0 and candidate_start <= manual_end + 1.0
        except (TypeError, ValueError):
            candidate_start = None
            candidate_end = None
            overlaps_manual = False
        if text_match:
            exact_candidate_ids.append(candidate_id)

        semantic = _by_candidate(analysis.get("semantic_decisions") or [], candidate_id)
        joins = _by_candidate(analysis.get("join_assessments") or [], candidate_id)
        eligibility = _by_candidate(analysis.get("eligibility_assessments") or [], candidate_id)
        promotions = _by_candidate(analysis.get("promotion_assessments") or [], candidate_id)
        acoustics: list[dict[str, Any]] = []
        for join in joins:
            acoustics.extend(
                _acoustic_for_join(
                    analysis.get("acoustic_join_assessments") or [],
                    str(join.get("id") or ""),
                )
            )
        candidate_records.append(
            {
                "candidate_id": candidate_id,
                "removed_text": removed,
                "text_match": text_match,
                "start": candidate_start,
                "end": candidate_end,
                "overlaps_manual": overlaps_manual,
                "semantic": [
                    {
                        "decision": item.get("decision"),
                        "guard_status": item.get("guard_status"),
                    }
                    for item in semantic
                ],
                "joins": [
                    {
                        "id": item.get("id"),
                        "status": item.get("status"),
                        "target_span": item.get("target_span"),
                    }
                    for item in joins
                ],
                "acoustics": [
                    {
                        "status": item.get("status"),
                        "measurement_available": item.get("measurement_available"),
                    }
                    for item in acoustics
                ],
                "eligibility": [
                    {
                        "status": item.get("status"),
                        "blockers": item.get("blockers"),
                        "future_promotion_candidate": item.get("future_promotion_candidate"),
                        "removed_text_validation": item.get("removed_text_validation"),
                    }
                    for item in eligibility
                ],
                "promotions": [
                    {
                        "status": item.get("status"),
                        "promotion_review_candidate": item.get("promotion_review_candidate"),
                        "approval_state": item.get("approval_state"),
                        "target_preview": item.get("target_preview"),
                    }
                    for item in promotions
                ],
            }
        )

    if not exact_candidate_ids:
        diagnosis = "exact_human_candidate_absent_from_canonical_candidate_set"
    else:
        exact_records = [item for item in candidate_records if item["candidate_id"] in exact_candidate_ids]
        if any(item["promotions"] for item in exact_records):
            diagnosis = "exact_human_candidate_reaches_promotion_layer"
        elif any(item["eligibility"] for item in exact_records):
            diagnosis = "exact_human_candidate_stops_at_or_after_eligibility"
        elif any(item["joins"] for item in exact_records):
            diagnosis = "exact_human_candidate_stops_at_or_after_join"
        elif any(item["semantic"] for item in exact_records):
            diagnosis = "exact_human_candidate_stops_at_or_after_semantic"
        else:
            diagnosis = "exact_human_candidate_present_without_linked_downstream_evidence"

    focus_start = max(0.0, manual_start - FOCUS_PADDING_SECONDS)
    focus_end = manual_end + FOCUS_PADDING_SECONDS
    excerpt = _excerpt_words(transcript, focus_start, focus_end)
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_case157_full_pipeline_diagnostic",
        "case_id": CASE_ID,
        "strategy": transcript.get("strategy"),
        "expected_removed_text": case["reparandum_text"],
        "manual_local_start": manual_start,
        "manual_local_end": manual_end,
        "canonical_excerpt_words": excerpt,
        "canonical_excerpt_text": " ".join(item["text"] for item in excerpt).strip(),
        "possible_repetition_records": candidate_records,
        "exact_candidate_ids": exact_candidate_ids,
        "diagnosis": diagnosis,
        "summary": analysis.get("summary"),
        "safety": {
            "product_default_changed": False,
            "canonical_merge_changed": False,
            "detector_or_guard_changed": False,
            "approval_created": False,
            "execution_authorization_created": False,
            "render_performed": False,
        },
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PHASE2E_CASE157_EXACT_CANDIDATES={len(exact_candidate_ids)}")
    print(f"PHASE2E_CASE157_DIAGNOSIS={diagnosis}")
    print(f"PHASE2E_CASE157_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
