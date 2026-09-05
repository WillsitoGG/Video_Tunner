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
from video_tunner.transcription import TranscriptResult, WHISPER_SAMPLE_RATE, _normalise_segments


WINDOW_START = 15.0
WINDOW_SECONDS = 12.0
TIMING_TOLERANCE_SECONDS = 0.75
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


def _transcribe_center(model: WhisperModel, master_audio: Path) -> TranscriptResult:
    audio = decode_audio(str(master_audio), sampling_rate=WHISPER_SAMPLE_RATE)
    start_sample = int(round(WINDOW_START * WHISPER_SAMPLE_RATE))
    end_sample = int(round((WINDOW_START + WINDOW_SECONDS) * WHISPER_SAMPLE_RATE))
    chunk = audio[start_sample:end_sample]
    raw_segments, info = model.transcribe(
        chunk,
        language="en",
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


def _evaluate_case(
    case: dict[str, Any],
    *,
    root: Path,
    ffmpeg: Path,
    model: WhisperModel,
) -> dict[str, Any]:
    case_id = str(case["id"])
    source_id = str(case["audio_source_id"])
    source_raw = os.environ.get(_source_env_name(source_id))
    if not source_raw or not Path(source_raw).is_file():
        raise RuntimeError(f"Missing AMI source for {case_id}")
    source = Path(source_raw)

    case_root = root / case_id
    case_root.mkdir(parents=True, exist_ok=True)
    clip_wav = case_root / "source_clip.wav"
    video = case_root / "aac_video.mp4"
    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])

    _run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(render_start), "-t", str(render_duration),
            "-i", str(source), "-ac", "1", "-ar", "16000",
            "-c:a", "pcm_s16le", str(clip_wav),
        ]
    )
    _run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", f"color=c=black:s=320x240:r=25:d={render_duration:.6f}",
            "-i", str(clip_wav), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(video),
        ]
    )

    ingest = ingest_video(video, case_root / "Ingest")
    if ingest.get("status") not in {"ready", "ready_auto", "ready_manual"}:
        raise RuntimeError(f"Ingest did not produce ready master for {case_id}: {ingest}")
    master = Path(str(ingest["master_audio"]))
    transcript = _transcribe_center(model, master)
    expected = _normalise_phrase(str(case["reparandum_text"]))
    matches: list[dict[str, Any]] = []
    for candidate in build_semantic_candidates(transcript, mode="conservative"):
        if candidate.get("kind") != case.get("expected_candidate_kind"):
            continue
        removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
        if _normalise_phrase(removed) != expected:
            continue
        local_start = WINDOW_START + float(candidate["start"])
        local_end = WINDOW_START + float(candidate["end"])
        manual_start = float(case["reparandum_start"]) - render_start
        manual_end = float(case["reparandum_end"]) - render_start
        start_delta = abs(local_start - manual_start)
        end_delta = abs(local_end - manual_end)
        timing_ok = start_delta <= TIMING_TOLERANCE_SECONDS and end_delta <= TIMING_TOLERANCE_SECONDS
        matches.append(
            {
                "removed_text": removed,
                "clip_local_start": round(local_start, 6),
                "clip_local_end": round(local_end, 6),
                "start_delta_seconds": round(start_delta, 6),
                "end_delta_seconds": round(end_delta, 6),
                "timing_ok": timing_ok,
            }
        )

    transcript_text = " ".join(segment.text for segment in transcript.segments if segment.text).strip()
    recovered = len([item for item in matches if item["timing_ok"]]) == 1
    record = {
        "id": case_id,
        "audio_source_id": source_id,
        "expected_text": case["reparandum_text"],
        "window_start": WINDOW_START,
        "window_end": WINDOW_START + WINDOW_SECONDS,
        "master_audio_source": "product_ingest_from_aac_mp4",
        "transcript": transcript_text,
        "matching_candidates": matches,
        "recovered": recovered,
    }
    print(f"PHASE2E_AAC_MASTER_CENTER_CASE={case_id} RECOVERED={int(recovered)}")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(
        str(Path(args.model_stage).resolve()),
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )

    cases = [
        _evaluate_case(case, root=output / "Cases", ffmpeg=Path(args.ffmpeg), model=model)
        for case in fixture.get("cases") or []
    ]
    recovered_count = sum(int(case["recovered"]) for case in cases)
    gate = "PASS" if len(cases) == 3 and recovered_count == 3 else "FAIL"
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_aac_master_center_window_diagnostic",
        "window_seconds": WINDOW_SECONDS,
        "window_start": WINDOW_START,
        "codec_path": "AMI PCM -> AAC MP4 -> product ingest master -> Whisper",
        "cases": cases,
        "recovered_count": recovered_count,
        "gate": gate,
        "safety": {
            "product_default_changed": False,
            "canonical_merge_changed": False,
            "detector_or_guard_changed": False,
            "approval_created": False,
            "render_performed": False,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PHASE2E_AAC_MASTER_CENTER_RECOVERED={recovered_count}/3")
    print(f"PHASE2E_AAC_MASTER_CENTER_GATE={gate}")
    print(f"PHASE2E_AAC_MASTER_CENTER_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
