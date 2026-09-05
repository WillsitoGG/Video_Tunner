from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import time
import unicodedata
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel

from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import TranscriptResult, _normalise_segments


_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _normalise_token(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _TOKEN_RE.sub("", asciiish)


def _normalise_phrase(text: str) -> list[str]:
    return [token for raw in text.split() if (token := _normalise_token(raw))]


def _audio_env_name(source_id: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", source_id.upper())
    return f"AMI_CLOSEOUT_{compact}_WAV"


def _grid_windows_for_span(
    span_start: float,
    span_end: float,
    *,
    window_seconds: float,
    hop_seconds: float,
    origin_seconds: float,
) -> list[float]:
    if window_seconds <= 0 or hop_seconds <= 0 or span_end <= span_start:
        raise ValueError("Invalid deterministic window geometry.")
    first_k = math.floor((span_start - window_seconds - origin_seconds) / hop_seconds) - 1
    last_k = math.floor((span_start - origin_seconds) / hop_seconds) + 1
    starts: list[float] = []
    for k in range(first_k, last_k + 1):
        start = origin_seconds + k * hop_seconds
        end = start + window_seconds
        if start < origin_seconds - 1e-9:
            continue
        if start <= span_start + 1e-9 and end >= span_end - 1e-9:
            starts.append(round(start, 6))
    return sorted(set(starts))


def _extract_clip(
    ffmpeg: Path,
    source: Path,
    destination: Path,
    *,
    start: float,
    duration: float,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.6f}",
            "-t",
            f"{duration:.6f}",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ],
        check=True,
    )


def _transcribe_window(
    model: WhisperModel,
    wav: Path,
    *,
    settings: dict[str, Any],
) -> tuple[TranscriptResult, float]:
    started = time.perf_counter()
    raw_segments, info = model.transcribe(
        str(wav),
        language=settings["language"],
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=bool(settings["condition_on_previous_text"]),
    )
    segments = _normalise_segments(raw_segments)
    result = TranscriptResult(
        language=getattr(info, "language", None),
        language_probability=(
            None
            if getattr(info, "language_probability", None) is None
            else float(info.language_probability)
        ),
        model=settings["model"],
        device=settings["device"],
        compute_type=settings["compute_type"],
        segments=segments,
    )
    return result, time.perf_counter() - started


def _score_window(
    transcript: TranscriptResult,
    *,
    window_start: float,
    expected_text: str,
    manual_start: float,
    manual_end: float,
    semantic_mode: str,
    timing_tolerance: float,
) -> dict[str, Any]:
    expected = _normalise_phrase(expected_text)
    candidates = build_semantic_candidates(transcript, mode=semantic_mode)
    repetitions = [item for item in candidates if item.get("kind") == "possible_repetition"]
    scored: list[dict[str, Any]] = []
    recovered = False
    for item in repetitions:
        removed_text = str((item.get("evidence") or {}).get("removed_text") or "")
        global_start = window_start + float(item["start"])
        global_end = window_start + float(item["end"])
        text_match = _normalise_phrase(removed_text) == expected
        start_delta = abs(global_start - manual_start)
        end_delta = abs(global_end - manual_end)
        timing_aligned = start_delta <= timing_tolerance and end_delta <= timing_tolerance
        is_match = text_match and timing_aligned
        recovered = recovered or is_match
        scored.append(
            {
                "removed_text": removed_text,
                "local_start": item["start"],
                "local_end": item["end"],
                "global_start": round(global_start, 6),
                "global_end": round(global_end, 6),
                "text_match": text_match,
                "start_delta_seconds": round(start_delta, 6),
                "end_delta_seconds": round(end_delta, 6),
                "timing_aligned": timing_aligned,
                "human_match": is_match,
            }
        )
    transcript_text = " ".join(segment.text for segment in transcript.segments if segment.text).strip()
    return {
        "word_count": transcript.word_count,
        "transcript": transcript_text,
        "possible_repetition_count": len(repetitions),
        "repetitions": scored,
        "recovered_human_case": recovered,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture_path = Path(args.fixture).resolve()
    model_stage = Path(args.model_stage).resolve()
    ffmpeg = Path(args.ffmpeg).resolve()
    output_root = Path(args.output).resolve()
    if not fixture_path.is_file():
        raise FileNotFoundError(f"Missing chunking fixture: {fixture_path}")
    if not model_stage.is_dir():
        raise FileNotFoundError(f"Missing pinned model stage: {model_stage}")
    if not ffmpeg.is_file():
        raise FileNotFoundError(f"Missing FFmpeg: {ffmpeg}")

    spec = json.loads(fixture_path.read_text(encoding="utf-8"))
    source_fixture_path = (Path.cwd() / spec["source_fixture"]).resolve()
    source_spec = json.loads(source_fixture_path.read_text(encoding="utf-8"))
    cases_by_id = {item["id"]: item for item in source_spec["cases"]}
    locked_ids = list(spec["locked_case_ids"])
    if set(locked_ids) != set(cases_by_id):
        raise RuntimeError("Chunking locked cases no longer match the source human corpus.")

    settings = spec["locked_settings"]
    timing_tolerance = float(settings["human_timing_tolerance_seconds"])
    origin = float(settings["grid_origin_seconds"])
    output_root.mkdir(parents=True, exist_ok=True)
    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    model = WhisperModel(
        str(model_stage),
        device=settings["device"],
        compute_type=settings["compute_type"],
        local_files_only=True,
    )

    profile_results: list[dict[str, Any]] = []
    selected_profile: str | None = None
    total_transcribe_seconds = 0.0
    total_windows = 0

    for profile in spec["profiles_in_preference_order"]:
        profile_id = str(profile["id"])
        window_seconds = float(profile["window_seconds"])
        hop_seconds = float(profile["hop_seconds"])
        case_results: list[dict[str, Any]] = []

        for case_id in locked_ids:
            case = cases_by_id[case_id]
            source_id = str(case["audio_source_id"])
            env_name = _audio_env_name(source_id)
            source_raw = os.environ.get(env_name)
            if not source_raw:
                raise RuntimeError(f"Missing AMI source environment variable {env_name} for {case_id}.")
            source_wav = Path(source_raw).resolve()
            if not source_wav.is_file():
                raise FileNotFoundError(f"Missing AMI source for {case_id}: {source_wav}")

            manual_start = float(case["reparandum_start"])
            manual_end = float(case["reparandum_end"])
            starts = _grid_windows_for_span(
                manual_start,
                manual_end,
                window_seconds=window_seconds,
                hop_seconds=hop_seconds,
                origin_seconds=origin,
            )
            if not starts:
                raise RuntimeError(f"Deterministic grid produced no covering window for {case_id}/{profile_id}.")

            windows: list[dict[str, Any]] = []
            case_recovered = False
            for index, start in enumerate(starts, start=1):
                wav = clips_root / profile_id / case_id / f"window-{index:02d}-{start:.3f}.wav"
                _extract_clip(
                    ffmpeg,
                    source_wav,
                    wav,
                    start=start,
                    duration=window_seconds,
                )
                transcript, elapsed = _transcribe_window(model, wav, settings=settings)
                total_transcribe_seconds += elapsed
                total_windows += 1
                scored = _score_window(
                    transcript,
                    window_start=start,
                    expected_text=str(case["reparandum_text"]),
                    manual_start=manual_start,
                    manual_end=manual_end,
                    semantic_mode=settings["semantic_mode"],
                    timing_tolerance=timing_tolerance,
                )
                scored.update(
                    {
                        "window_index": index,
                        "window_start": start,
                        "window_end": round(start + window_seconds, 6),
                        "elapsed_seconds": round(elapsed, 3),
                    }
                )
                windows.append(scored)
                case_recovered = case_recovered or bool(scored["recovered_human_case"])

            case_result = {
                "case_id": case_id,
                "audio_source_id": source_id,
                "expected_text": case["reparandum_text"],
                "manual_start": manual_start,
                "manual_end": manual_end,
                "covering_window_count": len(starts),
                "recovered": case_recovered,
                "windows": windows,
            }
            case_results.append(case_result)
            print(
                f"PHASE2E_CHUNK_CASE={case_id} PROFILE={profile_id} "
                f"RECOVERED={int(case_recovered)} WINDOWS={len(starts)}"
            )

        recovered_count = sum(int(item["recovered"]) for item in case_results)
        profile_pass = recovered_count == int(spec["success_policy"]["required_recovered_human_cases"])
        profile_record = {
            "profile": profile,
            "case_count": len(case_results),
            "recovered_human_cases": recovered_count,
            "passed": profile_pass,
            "cases": case_results,
        }
        profile_results.append(profile_record)
        print(
            f"PHASE2E_CHUNK_PROFILE={profile_id} RECOVERED={recovered_count}/{len(case_results)} "
            f"PASS={int(profile_pass)}"
        )
        if profile_pass:
            selected_profile = profile_id
            break

    policy = spec["success_policy"]
    decision = (
        policy["decision_if_profile_passes"]
        if selected_profile is not None
        else policy["decision_if_all_fail"]
    )
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_asr_deterministic_chunking_diagnostic",
        "source_fixture": spec["source_fixture"],
        "source_ab_run": spec["source_ab_run"],
        "settings": settings,
        "profiles_in_preference_order": spec["profiles_in_preference_order"],
        "selected_profile": selected_profile,
        "decision": decision,
        "total_windows_transcribed": total_windows,
        "total_transcribe_seconds": round(total_transcribe_seconds, 3),
        "safety": {
            "canonical_transcription_changed": False,
            "product_setting_changed": False,
            "detector_threshold_changed": False,
            "downstream_guard_changed": False,
            "edit_authorized": False,
            "render_performed": False,
        },
        "profile_results": profile_results,
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"PHASE2E_CHUNK_SELECTED_PROFILE={selected_profile or ''}")
    print(f"PHASE2E_CHUNK_DECISION={decision}")
    print(f"PHASE2E_CHUNK_TOTAL_WINDOWS={total_windows}")
    print("PHASE2E_CHUNK_DIAGNOSTIC=COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
