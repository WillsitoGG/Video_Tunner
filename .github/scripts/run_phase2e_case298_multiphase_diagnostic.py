from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from video_tunner.ingest import ingest_video
from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import (
    TranscriptResult,
    WHISPER_SAMPLE_RATE,
    _normalise_segments,
)


_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _normalise_phrase(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(
        token
        for raw in asciiish.split()
        if (token := _TOKEN_RE.sub("", raw))
    )


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


def _grid_starts(
    duration: float,
    *,
    window_seconds: float,
    hop_seconds: float,
    phase_seconds: float,
) -> list[float]:
    if duration <= 0 or window_seconds <= 0 or hop_seconds <= 0:
        raise ValueError("Invalid diagnostic grid geometry.")
    if phase_seconds < 0 or phase_seconds >= hop_seconds:
        raise ValueError("Phase offset must be inside one hop interval.")
    starts: list[float] = []
    start = phase_seconds
    while start < duration - 1e-9:
        starts.append(round(start, 6))
        start += hop_seconds
    return starts


def _transcribe_window(
    model: WhisperModel,
    audio,
    *,
    start: float,
    window_seconds: float,
    decoder: dict[str, Any],
) -> TranscriptResult:
    start_sample = int(round(start * WHISPER_SAMPLE_RATE))
    end_sample = int(round((start + window_seconds) * WHISPER_SAMPLE_RATE))
    chunk = audio[start_sample:end_sample]
    raw_segments, info = model.transcribe(
        chunk,
        language=decoder["language"],
        word_timestamps=bool(decoder["word_timestamps"]),
        vad_filter=bool(decoder["vad_filter"]),
        condition_on_previous_text=bool(decoder["condition_on_previous_text"]),
    )
    return TranscriptResult(
        language=getattr(info, "language", None),
        language_probability=(
            None
            if getattr(info, "language_probability", None) is None
            else float(info.language_probability)
        ),
        model=str(decoder["model"]),
        device=str(decoder["device"]),
        compute_type=str(decoder["compute_type"]),
        segments=_normalise_segments(raw_segments),
    )


def _score_window(
    transcript: TranscriptResult,
    *,
    window_start: float,
    expected_text: str,
    candidate_kind: str,
    manual_local_start: float,
    manual_local_end: float,
    timing_tolerance: float,
) -> dict[str, Any]:
    transcript_text = " ".join(
        segment.text for segment in transcript.segments if segment.text
    ).strip()
    matches: list[dict[str, Any]] = []
    candidates = build_semantic_candidates(transcript, mode="conservative")
    for candidate in candidates:
        if candidate.get("kind") != candidate_kind:
            continue
        removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
        if _normalise_phrase(removed) != _normalise_phrase(expected_text):
            continue
        local_start = window_start + float(candidate["start"])
        local_end = window_start + float(candidate["end"])
        start_delta = abs(local_start - manual_local_start)
        end_delta = abs(local_end - manual_local_end)
        timing_ok = (
            start_delta <= timing_tolerance
            and end_delta <= timing_tolerance
        )
        matches.append(
            {
                "candidate_id": candidate.get("id"),
                "removed_text": removed,
                "clip_local_start": round(local_start, 6),
                "clip_local_end": round(local_end, 6),
                "start_delta_seconds": round(start_delta, 6),
                "end_delta_seconds": round(end_delta, 6),
                "timing_ok": timing_ok,
            }
        )
    aligned = [item for item in matches if item["timing_ok"]]
    return {
        "transcript": transcript_text,
        "word_count": transcript.word_count,
        "matching_candidates": matches,
        "aligned_match_count": len(aligned),
        "recovered": len(aligned) >= 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    source_fixture_path = (Path.cwd() / spec["source_fixture"]).resolve()
    source_fixture = json.loads(source_fixture_path.read_text(encoding="utf-8"))
    case = next(
        (item for item in source_fixture.get("cases") or [] if item.get("id") == spec["case_id"]),
        None,
    )
    if case is None:
        raise RuntimeError(f"Missing locked human case {spec['case_id']}.")

    source_id = str(case["audio_source_id"])
    source_raw = os.environ.get(_source_env_name(source_id))
    if not source_raw or not Path(source_raw).is_file():
        raise RuntimeError(f"Missing AMI source for {source_id}.")

    ffmpeg = Path(args.ffmpeg).resolve()
    model_stage = Path(args.model_stage).resolve()
    output_root = Path(args.output).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    media_root = output_root / "Media"
    media_root.mkdir(parents=True, exist_ok=True)

    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])
    source_clip = media_root / "case298-source.wav"
    video = media_root / "case298-aac.mp4"
    _run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(render_start), "-t", str(render_duration),
            "-i", str(Path(source_raw)), "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(source_clip),
        ]
    )
    _run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i",
            f"color=c=black:s=320x240:r=25:d={render_duration:.6f}",
            "-i", str(source_clip), "-shortest", "-c:v", "libx264",
            "-pix_fmt", "yuv420p", "-c:a", "aac", str(video),
        ]
    )

    ingest = ingest_video(video, output_root / "Ingest")
    if ingest.get("status") not in {"ready", "ready_auto", "ready_manual"}:
        raise RuntimeError(f"Ingest did not produce a ready master: {ingest}")
    master_audio = Path(str(ingest["master_audio"]))
    audio = decode_audio(str(master_audio), sampling_rate=WHISPER_SAMPLE_RATE)
    duration = len(audio) / float(WHISPER_SAMPLE_RATE)

    decoder = spec["decoder"]
    model = WhisperModel(
        str(model_stage),
        device=decoder["device"],
        compute_type=decoder["compute_type"],
        local_files_only=True,
    )

    grid = spec["grid"]
    window_seconds = float(grid["window_seconds"])
    hop_seconds = float(grid["hop_seconds"])
    phases = [float(value) for value in grid["phase_offsets_seconds"]]
    evaluation = spec["evaluation"]
    timing_tolerance = float(evaluation["timing_tolerance_seconds"])
    expected_text = str(case["reparandum_text"])
    manual_local_start = float(case["reparandum_start"]) - render_start
    manual_local_end = float(case["reparandum_end"]) - render_start

    phase_results: list[dict[str, Any]] = []
    total_windows = 0
    recovered_phases: list[float] = []
    for phase in phases:
        starts = _grid_starts(
            duration,
            window_seconds=window_seconds,
            hop_seconds=hop_seconds,
            phase_seconds=phase,
        )
        windows: list[dict[str, Any]] = []
        phase_recovered = False
        for index, start in enumerate(starts):
            transcript = _transcribe_window(
                model,
                audio,
                start=start,
                window_seconds=window_seconds,
                decoder=decoder,
            )
            scored = _score_window(
                transcript,
                window_start=start,
                expected_text=expected_text,
                candidate_kind=str(evaluation["candidate_kind"]),
                manual_local_start=manual_local_start,
                manual_local_end=manual_local_end,
                timing_tolerance=timing_tolerance,
            )
            scored.update(
                {
                    "index": index,
                    "start": start,
                    "end": round(min(duration, start + window_seconds), 6),
                }
            )
            windows.append(scored)
            phase_recovered = phase_recovered or bool(scored["recovered"])
            total_windows += 1
        if phase_recovered:
            recovered_phases.append(phase)
        phase_results.append(
            {
                "phase_offset_seconds": phase,
                "window_count": len(windows),
                "recovered": phase_recovered,
                "windows": windows,
            }
        )
        print(
            f"PHASE2E_CASE298_PHASE={phase:.1f} "
            f"RECOVERED={int(phase_recovered)} WINDOWS={len(windows)}"
        )

    any_recovered = bool(recovered_phases)
    decision = (
        evaluation["product_decision_if_recovered"]
        if any_recovered
        else evaluation["product_decision_if_not_recovered"]
    )
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_case298_multiphase_diagnostic",
        "spec": spec_path.name,
        "case_id": case["id"],
        "audio_source_id": source_id,
        "expected_text": expected_text,
        "manual_local_start": round(manual_local_start, 6),
        "manual_local_end": round(manual_local_end, 6),
        "master_audio_source": "product_ingest_from_aac_mp4",
        "master_duration_seconds": round(duration, 6),
        "grid": grid,
        "decoder": decoder,
        "total_windows_transcribed": total_windows,
        "recovered_phase_offsets_seconds": recovered_phases,
        "any_phase_recovered": any_recovered,
        "decision": decision,
        "phase_results": phase_results,
        "safety": spec["safety"],
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"PHASE2E_CASE298_RECOVERED_PHASES={','.join(str(v) for v in recovered_phases)}")
    print(f"PHASE2E_CASE298_ANY_PHASE_RECOVERED={int(any_recovered)}")
    print(f"PHASE2E_CASE298_TOTAL_WINDOWS={total_windows}")
    print(f"PHASE2E_CASE298_DECISION={decision}")
    print(f"PHASE2E_CASE298_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
