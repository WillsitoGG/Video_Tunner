from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import TranscriptResult, _normalise_segments

SAMPLE_RATE = 16000
WINDOW_SECONDS = 12.0
PROPOSED_HOP_SECONDS = 3.0
EVENT_OWNER_START_SECONDS = 15.0
EVENT_OWNER_START_OWNERSHIP = 19.5
EVENT_OWNER_END_OWNERSHIP = 22.5
TIMING_TOLERANCE_SECONDS = 0.75


def _norm(text: str | None) -> list[str]:
    if not text:
        return []
    result = []
    for raw in text.lower().split():
        decomposed = unicodedata.normalize("NFKD", raw)
        token = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
        token = re.sub(r"[^a-z0-9]+", "", token)
        if token:
            result.append(token)
    return result


def _env_name(source_id: str) -> str:
    return "AMI_CLOSEOUT_" + re.sub(r"[^A-Z0-9]", "", source_id.upper()) + "_WAV"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        str(Path(args.model_stage).resolve()),
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )

    audio_cache = {}
    results = []
    for case in fixture["cases"]:
        case_id = str(case["id"])
        source_id = str(case["audio_source_id"])
        if source_id not in audio_cache:
            value = os.environ.get(_env_name(source_id))
            if not value or not Path(value).is_file():
                raise RuntimeError(f"Missing AMI source for {case_id}/{source_id}")
            audio_cache[source_id] = decode_audio(value, sampling_rate=SAMPLE_RATE)

        render_start = float(case["render_clip_start"])
        manual_start = float(case["reparandum_start"]) - render_start
        manual_end = float(case["reparandum_end"]) - render_start
        if not (
            manual_start >= EVENT_OWNER_START_OWNERSHIP - 1e-9
            and manual_end <= EVENT_OWNER_END_OWNERSHIP + 1e-9
        ):
            raise RuntimeError(
                f"Precommitted 12/3 owner window does not fully own label {case_id}: "
                f"{manual_start:.3f}-{manual_end:.3f}"
            )

        absolute_start = render_start + EVENT_OWNER_START_SECONDS
        start_sample = int(round(absolute_start * SAMPLE_RATE))
        end_sample = int(round((absolute_start + WINDOW_SECONDS) * SAMPLE_RATE))
        chunk = audio_cache[source_id][start_sample:end_sample]
        raw_segments, info = model.transcribe(
            chunk,
            language="en",
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=True,
        )
        transcript = TranscriptResult(
            language=getattr(info, "language", None),
            language_probability=(
                None if getattr(info, "language_probability", None) is None else float(info.language_probability)
            ),
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=_normalise_segments(raw_segments),
        )
        expected = _norm(str(case["reparandum_text"]))
        matches = []
        for candidate in build_semantic_candidates(transcript, mode="conservative"):
            if candidate.get("kind") != "possible_repetition":
                continue
            removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
            local_start = EVENT_OWNER_START_SECONDS + float(candidate["start"])
            local_end = EVENT_OWNER_START_SECONDS + float(candidate["end"])
            text_match = _norm(removed) == expected
            start_delta = abs(local_start - manual_start)
            end_delta = abs(local_end - manual_end)
            timing_ok = start_delta <= TIMING_TOLERANCE_SECONDS and end_delta <= TIMING_TOLERANCE_SECONDS
            matches.append(
                {
                    "removed_text": removed,
                    "clip_local_start": round(local_start, 6),
                    "clip_local_end": round(local_end, 6),
                    "text_match": text_match,
                    "start_delta_seconds": round(start_delta, 6),
                    "end_delta_seconds": round(end_delta, 6),
                    "timing_ok": timing_ok,
                    "human_match": text_match and timing_ok,
                }
            )
        recovered = sum(bool(item["human_match"]) for item in matches) == 1
        record = {
            "id": case_id,
            "audio_source_id": source_id,
            "expected_text": case["reparandum_text"],
            "manual_local_start": round(manual_start, 6),
            "manual_local_end": round(manual_end, 6),
            "owner_window_start": EVENT_OWNER_START_SECONDS,
            "owner_window_end": EVENT_OWNER_START_SECONDS + WINDOW_SECONDS,
            "owner_region_start": EVENT_OWNER_START_OWNERSHIP,
            "owner_region_end": EVENT_OWNER_END_OWNERSHIP,
            "transcript": " ".join(segment.text for segment in transcript.segments if segment.text).strip(),
            "possible_repetition_matches": matches,
            "recovered": recovered,
        }
        results.append(record)
        print(f"PHASE2E_12S3S_CENTER_CASE={case_id} RECOVERED={int(recovered)}")

    recovered_count = sum(int(item["recovered"]) for item in results)
    gate_pass = recovered_count == 3
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_12s3s_center_window_diagnostic",
        "source_local_grid_run": 33971900932,
        "profile": {
            "window_seconds": WINDOW_SECONDS,
            "hop_seconds": PROPOSED_HOP_SECONDS,
            "overlap_fraction": 0.75,
            "merge_policy": "existing_midpoint_ownership_geometry_only",
        },
        "precommitted_event_owner_window": {
            "start": EVENT_OWNER_START_SECONDS,
            "end": EVENT_OWNER_START_SECONDS + WINDOW_SECONDS,
            "ownership_start": EVENT_OWNER_START_OWNERSHIP,
            "ownership_end": EVENT_OWNER_END_OWNERSHIP,
        },
        "success_policy": "3/3 exact human repetitions within ±0.75s or reject 12s/3s profile",
        "cases": results,
        "recovered_count": recovered_count,
        "gate": "PASS" if gate_pass else "FAIL",
        "safety": {
            "product_default_changed": False,
            "canonical_transcription_changed": False,
            "detector_or_guard_changed": False,
            "approval_created": False,
            "render_performed": False,
        },
    }
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PHASE2E_12S3S_CENTER_RECOVERED={recovered_count}/3")
    print(f"PHASE2E_12S3S_CENTER_GATE={manifest['gate']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
