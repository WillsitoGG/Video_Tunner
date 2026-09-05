from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import TranscriptResult, _normalise_segments

SAMPLE_RATE = 16000
WINDOW_SECONDS = 12.0
LOCAL_WINDOW_STARTS = (12.0, 18.0)
TIMING_TOLERANCE_SECONDS = 0.75


def _norm_token(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", asciiish)


def _norm_phrase(text: str | None) -> list[str]:
    if not text:
        return []
    return [token for raw in text.split() if (token := _norm_token(raw))]


def _phrase_occurrences(words: list[str], expected: list[str]) -> list[int]:
    normalised = [_norm_token(word) for word in words]
    if not expected:
        return []
    return [
        index
        for index in range(0, len(normalised) - len(expected) + 1)
        if normalised[index : index + len(expected)] == expected
    ]


def _source_env_name(source_id: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", source_id.upper())
    return f"AMI_CLOSEOUT_{compact}_WAV"


def _transcript_from_chunk(
    model: WhisperModel,
    audio,
    *,
    language: str,
) -> TranscriptResult:
    raw_segments, info = model.transcribe(
        audio,
        language=language,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=True,
    )
    return TranscriptResult(
        language=getattr(info, "language", None),
        language_probability=(
            None
            if getattr(info, "language_probability", None) is None
            else float(info.language_probability)
        ),
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=_normalise_segments(raw_segments),
    )


def _score_window(
    transcript: TranscriptResult,
    *,
    local_window_start: float,
    expected_text: str,
    manual_local_start: float,
    manual_local_end: float,
) -> dict[str, Any]:
    words = [
        word.text
        for segment in transcript.segments
        for word in segment.words
        if word.text
    ]
    expected = _norm_phrase(expected_text)
    raw_occurrences = _phrase_occurrences(words, expected)
    semantic = build_semantic_candidates(transcript, mode="conservative")
    repetitions = [item for item in semantic if item.get("kind") == "possible_repetition"]
    scored_repetitions = []
    recovered = False
    for item in repetitions:
        removed = str((item.get("evidence") or {}).get("removed_text") or "")
        local_start = local_window_start + float(item["start"])
        local_end = local_window_start + float(item["end"])
        text_match = _norm_phrase(removed) == expected
        start_delta = abs(local_start - manual_local_start)
        end_delta = abs(local_end - manual_local_end)
        timing_ok = start_delta <= TIMING_TOLERANCE_SECONDS and end_delta <= TIMING_TOLERANCE_SECONDS
        human_match = text_match and timing_ok
        recovered = recovered or human_match
        scored_repetitions.append(
            {
                "removed_text": removed,
                "window_relative_start": item["start"],
                "window_relative_end": item["end"],
                "clip_local_start": round(local_start, 6),
                "clip_local_end": round(local_end, 6),
                "text_match": text_match,
                "start_delta_seconds": round(start_delta, 6),
                "end_delta_seconds": round(end_delta, 6),
                "timing_ok": timing_ok,
                "human_match": human_match,
            }
        )
    return {
        "local_window_start": local_window_start,
        "local_window_end": local_window_start + WINDOW_SECONDS,
        "word_count": len(words),
        "transcript": " ".join(segment.text for segment in transcript.segments if segment.text).strip(),
        "expected_phrase_raw_occurrence_count": len(raw_occurrences),
        "expected_phrase_raw_occurrence_word_indices": raw_occurrences,
        "possible_repetition_count": len(repetitions),
        "repetitions": scored_repetitions,
        "recovered_human_case": recovered,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    model_stage = Path(args.model_stage).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)

    model = WhisperModel(
        str(model_stage),
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )

    decoded_by_source: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    for case in fixture["cases"]:
        case_id = str(case["id"])
        source_id = str(case["audio_source_id"])
        if source_id not in decoded_by_source:
            env_name = _source_env_name(source_id)
            source_raw = os.environ.get(env_name)
            if not source_raw or not Path(source_raw).is_file():
                raise RuntimeError(f"Missing AMI source {env_name} for {case_id}")
            decoded_by_source[source_id] = decode_audio(source_raw, sampling_rate=SAMPLE_RATE)

        source_audio = decoded_by_source[source_id]
        render_start = float(case["render_clip_start"])
        manual_local_start = float(case["reparandum_start"]) - render_start
        manual_local_end = float(case["reparandum_end"]) - render_start
        expected_text = str(case["reparandum_text"])
        windows = []
        for local_start in LOCAL_WINDOW_STARTS:
            absolute_start = render_start + local_start
            start_sample = int(round(absolute_start * SAMPLE_RATE))
            end_sample = int(round((absolute_start + WINDOW_SECONDS) * SAMPLE_RATE))
            chunk = source_audio[start_sample:end_sample]
            transcript = _transcript_from_chunk(model, chunk, language="en")
            scored = _score_window(
                transcript,
                local_window_start=local_start,
                expected_text=expected_text,
                manual_local_start=manual_local_start,
                manual_local_end=manual_local_end,
            )
            scored["absolute_window_start"] = round(absolute_start, 6)
            scored["absolute_window_end"] = round(absolute_start + WINDOW_SECONDS, 6)
            windows.append(scored)

        any_raw = any(item["expected_phrase_raw_occurrence_count"] > 0 for item in windows)
        any_recovered = any(item["recovered_human_case"] for item in windows)
        if not any_raw:
            diagnosis = "LOCAL_GRID_PHASE_ASR_LOSS"
        elif any_recovered:
            diagnosis = "RAW_WINDOW_RECOVERS_EXPECTED_REPETITION"
        else:
            diagnosis = "EXPECTED_TEXT_PRESENT_BUT_SEMANTIC_OR_TIMING_MISS"
        record = {
            "id": case_id,
            "audio_source_id": source_id,
            "expected_text": expected_text,
            "manual_local_start": round(manual_local_start, 6),
            "manual_local_end": round(manual_local_end, 6),
            "windows": windows,
            "any_raw_expected_phrase": any_raw,
            "any_recovered_human_case": any_recovered,
            "diagnosis": diagnosis,
        }
        results.append(record)
        print(
            f"PHASE2E_LOCAL_GRID_CASE={case_id} RAW={int(any_raw)} "
            f"RECOVERED={int(any_recovered)} DIAGNOSIS={diagnosis}"
        )

    phase_loss = sum(item["diagnosis"] == "LOCAL_GRID_PHASE_ASR_LOSS" for item in results)
    raw_recovered = sum(item["any_recovered_human_case"] for item in results)
    semantic_miss = sum(
        item["diagnosis"] == "EXPECTED_TEXT_PRESENT_BUT_SEMANTIC_OR_TIMING_MISS"
        for item in results
    )
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_local_grid_phase_diagnostic",
        "source_fixture": Path(args.fixture).name,
        "source_full_pipeline_gate_run": 33971387119,
        "source_global_grid_success_run": 33967219217,
        "model": "large-v3-turbo",
        "device": "cpu",
        "compute_type": "int8",
        "language": "en",
        "window_seconds": WINDOW_SECONDS,
        "local_window_starts": list(LOCAL_WINDOW_STARTS),
        "grid_origin": "render_context_local_t0",
        "timing_tolerance_seconds": TIMING_TOLERANCE_SECONDS,
        "cases": results,
        "summary": {
            "case_count": len(results),
            "local_grid_phase_asr_loss": phase_loss,
            "raw_window_human_repetition_recovered": raw_recovered,
            "expected_text_present_semantic_or_timing_miss": semantic_miss,
        },
        "safety": {
            "product_default_changed": False,
            "cli_changed": False,
            "detector_threshold_changed": False,
            "downstream_guard_changed": False,
            "approval_created": False,
            "render_performed": False,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PHASE2E_LOCAL_GRID_PHASE_LOSS={phase_loss}/3")
    print(f"PHASE2E_LOCAL_GRID_RAW_RECOVERED={raw_recovered}/3")
    print(f"PHASE2E_LOCAL_GRID_SEMANTIC_MISS={semantic_miss}/3")
    print(f"PHASE2E_LOCAL_GRID_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
