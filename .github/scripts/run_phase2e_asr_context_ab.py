from __future__ import annotations

import argparse
import hashlib
import json
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _audio_env_name(source_id: str) -> str:
    compact = re.sub(r"[^A-Z0-9]", "", source_id.upper())
    return f"AMI_CLOSEOUT_{compact}_WAV"


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


def _transcript_text(result: TranscriptResult) -> str:
    return " ".join(segment.text for segment in result.segments if segment.text).strip()


def _excerpt(result: TranscriptResult, *, center: float, radius: float = 5.0) -> str:
    words = [word for segment in result.segments for word in segment.words]
    selected = [
        word.text
        for word in words
        if word.end >= center - radius and word.start <= center + radius
    ]
    return " ".join(selected).strip()


def _transcribe_once(
    model: WhisperModel,
    wav: Path,
    *,
    model_name: str,
    language: str,
    device: str,
    compute_type: str,
    condition_on_previous_text: bool,
    semantic_mode: str,
    manual_center_seconds: float,
) -> dict[str, Any]:
    started = time.perf_counter()
    raw_segments, info = model.transcribe(
        str(wav),
        language=language,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=condition_on_previous_text,
    )
    segments = _normalise_segments(raw_segments)
    result = TranscriptResult(
        language=getattr(info, "language", None),
        language_probability=(
            None
            if getattr(info, "language_probability", None) is None
            else float(info.language_probability)
        ),
        model=model_name,
        device=device,
        compute_type=compute_type,
        segments=segments,
    )
    candidates = build_semantic_candidates(result, mode=semantic_mode)
    repetitions = [item for item in candidates if item.get("kind") == "possible_repetition"]
    return {
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "language": result.language,
        "language_probability": result.language_probability,
        "word_count": result.word_count,
        "transcript": _transcript_text(result),
        "manual_region_excerpt": _excerpt(result, center=manual_center_seconds),
        "possible_repetition_count": len(repetitions),
        "possible_repetitions": [
            {
                "start": item.get("start"),
                "end": item.get("end"),
                "removed_text": (item.get("evidence") or {}).get("removed_text"),
                "first_occurrence_text": (item.get("evidence") or {}).get("first_occurrence_text"),
                "second_occurrence_text": (item.get("evidence") or {}).get("second_occurrence_text"),
                "repeat_token_count": (item.get("evidence") or {}).get("repeat_token_count"),
            }
            for item in repetitions
        ],
    }


def _add_exact_match_fields(record: dict[str, Any], expected_text: str) -> None:
    expected = _normalise_phrase(expected_text)
    matches = [
        item
        for item in record["possible_repetitions"]
        if _normalise_phrase(str(item.get("removed_text") or "")) == expected
    ]
    record["expected_text"] = expected_text
    record["exact_expected_match_count"] = len(matches)
    record["exact_expected_match"] = len(matches) > 0
    record["exact_matches"] = matches


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
        raise FileNotFoundError(f"Missing A/B fixture: {fixture_path}")
    if not model_stage.is_dir():
        raise FileNotFoundError(f"Missing pinned model stage: {model_stage}")
    if not ffmpeg.is_file():
        raise FileNotFoundError(f"Missing FFmpeg: {ffmpeg}")

    spec = json.loads(fixture_path.read_text(encoding="utf-8"))
    source_fixture = (Path.cwd() / spec["source_fixture"]).resolve()
    source = json.loads(source_fixture.read_text(encoding="utf-8"))
    cases_by_id = {case["id"]: case for case in source["cases"]}
    locked_ids = list(spec["locked_case_ids"])
    if set(locked_ids) != set(cases_by_id):
        raise RuntimeError("A/B locked cases no longer match the source human close-out fixture.")

    settings = spec["locked_settings"]
    output_root.mkdir(parents=True, exist_ok=True)
    clips_root = output_root / "clips"
    clips_root.mkdir(parents=True, exist_ok=True)

    model = WhisperModel(
        str(model_stage),
        device=settings["device"],
        compute_type=settings["compute_type"],
        local_files_only=True,
    )

    arms = {
        "baseline": bool(spec["arms"]["baseline"]["condition_on_previous_text"]),
        "challenger": bool(spec["arms"]["challenger"]["condition_on_previous_text"]),
    }
    results: list[dict[str, Any]] = []

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

        case_root = clips_root / case_id
        short_wav = case_root / "short.wav"
        long_wav = case_root / "long.wav"
        _extract_clip(
            ffmpeg,
            source_wav,
            short_wav,
            start=float(case["clip_start"]),
            duration=float(case["clip_duration"]),
        )
        _extract_clip(
            ffmpeg,
            source_wav,
            long_wav,
            start=float(case["render_clip_start"]),
            duration=float(case["render_clip_duration"]),
        )

        case_record: dict[str, Any] = {
            "case_id": case_id,
            "audio_source_id": source_id,
            "human_label": case["human_label"],
            "expected_text": case["reparandum_text"],
            "clips": {
                "short": {
                    "start": case["clip_start"],
                    "duration": case["clip_duration"],
                    "sha256": _sha256(short_wav),
                },
                "long": {
                    "start": case["render_clip_start"],
                    "duration": case["render_clip_duration"],
                    "sha256": _sha256(long_wav),
                },
            },
            "arms": {},
        }

        for arm_name, condition in arms.items():
            arm_record: dict[str, Any] = {}
            for context_name, wav, clip_start in (
                ("short", short_wav, float(case["clip_start"])),
                ("long", long_wav, float(case["render_clip_start"])),
            ):
                manual_center = (
                    (float(case["reparandum_start"]) + float(case["reparandum_end"])) / 2.0
                    - clip_start
                )
                record = _transcribe_once(
                    model,
                    wav,
                    model_name=settings["model"],
                    language=settings["language"],
                    device=settings["device"],
                    compute_type=settings["compute_type"],
                    condition_on_previous_text=condition,
                    semantic_mode=settings["semantic_mode"],
                    manual_center_seconds=manual_center,
                )
                _add_exact_match_fields(record, str(case["reparandum_text"]))
                arm_record[context_name] = record
                print(
                    f"PHASE2E_ASR_AB_CASE={case_id} ARM={arm_name} CONTEXT={context_name} "
                    f"EXACT={int(record['exact_expected_match'])} "
                    f"REPEATS={record['possible_repetition_count']} "
                    f"SECONDS={record['elapsed_seconds']}"
                )
            case_record["arms"][arm_name] = arm_record
        results.append(case_record)

    baseline_short = sum(
        int(case["arms"]["baseline"]["short"]["exact_expected_match"]) for case in results
    )
    baseline_long = sum(
        int(case["arms"]["baseline"]["long"]["exact_expected_match"]) for case in results
    )
    challenger_short = sum(
        int(case["arms"]["challenger"]["short"]["exact_expected_match"]) for case in results
    )
    challenger_long = sum(
        int(case["arms"]["challenger"]["long"]["exact_expected_match"]) for case in results
    )

    policy = spec["success_policy"]
    passed = (
        len(results) == int(policy["required_case_count"])
        and challenger_short == int(policy["required_challenger_short_exact_matches"])
        and challenger_long == int(policy["required_challenger_long_exact_matches"])
    )
    decision = policy["decision_if_pass"] if passed else policy["decision_if_fail"]
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_asr_context_ab_diagnostic",
        "source_fixture": spec["source_fixture"],
        "source_diagnostic_run": spec["source_diagnostic_run"],
        "settings": settings,
        "arms": spec["arms"],
        "case_count": len(results),
        "summary": {
            "baseline_short_exact_matches": baseline_short,
            "baseline_long_exact_matches": baseline_long,
            "challenger_short_exact_matches": challenger_short,
            "challenger_long_exact_matches": challenger_long,
            "challenger_passed_precommitted_gate": passed,
            "decision": decision,
        },
        "safety": {
            "product_setting_changed": False,
            "detector_threshold_changed": False,
            "downstream_guard_changed": False,
            "edit_authorized": False,
            "render_performed": False,
        },
        "cases": results,
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"PHASE2E_ASR_AB_BASELINE_SHORT={baseline_short}")
    print(f"PHASE2E_ASR_AB_BASELINE_LONG={baseline_long}")
    print(f"PHASE2E_ASR_AB_CHALLENGER_SHORT={challenger_short}")
    print(f"PHASE2E_ASR_AB_CHALLENGER_LONG={challenger_long}")
    print(f"PHASE2E_ASR_AB_DECISION={decision}")
    print("PHASE2E_ASR_AB_DIAGNOSTIC=COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
