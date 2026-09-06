from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio

from video_tunner.ingest import ingest_video
from video_tunner.transcription import (
    WHISPER_SAMPLE_RATE,
    _normalise_segments,
    build_transcription_chunk_windows,
)
from video_tunner.transcription_consensus import _repeat_hypotheses

CASE_ID = "ami-ts3005d-c-repeat-298"
WINDOW_SECONDS = 12.0
HOP_SECONDS = 3.0
FOCUS_INDICES = (4, 5, 6)
EXPECTED_PHRASE = ("and", "then", "you", "can")
EXPECTED_FFMPEG_ARCHIVE_SHA256 = "87c4729f3193f3ba562bada0330a98338c9a858d25b15fc98338a1364667348b"


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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _segments_record(window: Any, segments: tuple[Any, ...]) -> dict[str, Any]:
    hypotheses = _repeat_hypotheses(window, segments)
    expected = [item for item in hypotheses if item.phrase == EXPECTED_PHRASE]
    words: list[dict[str, Any]] = []
    for segment in segments:
        for word in segment.words:
            global_start = window.start + float(word.start)
            global_end = window.start + float(word.end)
            words.append(
                {
                    "text": word.text,
                    "start": round(global_start, 6),
                    "end": round(global_end, 6),
                    "midpoint": round((global_start + global_end) / 2.0, 6),
                    "probability": word.probability,
                }
            )
    return {
        "index": window.index,
        "start": window.start,
        "end": window.end,
        "ownership_start": window.ownership_start,
        "ownership_end": window.ownership_end,
        "transcript": " ".join(segment.text for segment in segments if segment.text).strip(),
        "words": words,
        "expected_repeat_count": len(expected),
        "expected_repeats": [
            {
                "first_start": round(float(item.first_start), 6),
                "first_end": round(float(item.first_end), 6),
                "second_start": round(float(item.second_start), 6),
                "second_end": round(float(item.second_end), 6),
                "words": [word.text for word in item.words],
            }
            for item in expected
        ],
    }


def _run_arm(
    *,
    name: str,
    model_stage: Path,
    audio: Any,
    windows: tuple[Any, ...],
    indices: tuple[int, ...],
) -> dict[str, Any]:
    model = WhisperModel(
        str(model_stage),
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )
    focus: dict[int, dict[str, Any]] = {}
    processed: list[int] = []
    for index in indices:
        window = windows[index]
        start_sample = int(round(window.start * WHISPER_SAMPLE_RATE))
        end_sample = int(round(window.end * WHISPER_SAMPLE_RATE))
        raw_segments, _info = model.transcribe(
            audio[start_sample:end_sample],
            language="en",
            word_timestamps=True,
            vad_filter=False,
            condition_on_previous_text=True,
        )
        segments = _normalise_segments(raw_segments)
        processed.append(index)
        if index in FOCUS_INDICES:
            focus[index] = _segments_record(window, segments)
    del model
    gc.collect()
    return {
        "name": name,
        "processed_indices": processed,
        "focus_windows": [focus[index] for index in FOCUS_INDICES],
        "focus_signature": [
            {
                "index": index,
                "transcript": focus[index]["transcript"],
                "expected_repeat_count": focus[index]["expected_repeat_count"],
            }
            for index in FOCUS_INDICES
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--ffmpeg-archive-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    ffmpeg_archive_sha = str(args.ffmpeg_archive_sha256).strip().lower()
    if ffmpeg_archive_sha != EXPECTED_FFMPEG_ARCHIVE_SHA256:
        raise RuntimeError(
            f"FFmpeg archive SHA mismatch: {ffmpeg_archive_sha} != {EXPECTED_FFMPEG_ARCHIVE_SHA256}"
        )

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    case = next(item for item in fixture.get("cases") or [] if item.get("id") == CASE_ID)
    source_id = str(case["audio_source_id"])
    source_raw = os.environ.get(_source_env_name(source_id))
    if not source_raw or not Path(source_raw).is_file():
        raise RuntimeError(f"Missing AMI source: {source_id}")

    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    ffmpeg = Path(args.ffmpeg).resolve()
    clip_wav = output / "source_clip.wav"
    video = output / "aac_video.mp4"
    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])

    _run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-ss", str(render_start), "-t", str(render_duration), "-i", source_raw,
        "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(clip_wav),
    ])
    _run([
        str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=black:s=320x240:r=25:d={render_duration:.6f}",
        "-i", str(clip_wav), "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", str(video),
    ])

    ingest = ingest_video(video, output / "Ingest")
    if ingest.get("status") != "ready":
        raise RuntimeError(f"Embedded ingest did not return ready: {ingest}")
    master = Path(str(ingest["master_audio"]))
    audio = decode_audio(str(master), sampling_rate=WHISPER_SAMPLE_RATE)
    duration = float(len(audio)) / float(WHISPER_SAMPLE_RATE)
    windows = build_transcription_chunk_windows(
        duration,
        window_seconds=WINDOW_SECONDS,
        hop_seconds=HOP_SECONDS,
    )
    if len(windows) <= max(FOCUS_INDICES):
        raise RuntimeError(f"Insufficient windows: {len(windows)}")

    model_stage = Path(args.model_stage).resolve()
    direct = _run_arm(
        name="fresh_model_direct_focus_4_5_6",
        model_stage=model_stage,
        audio=audio,
        windows=windows,
        indices=FOCUS_INDICES,
    )
    prefix = _run_arm(
        name="fresh_model_product_prefix_0_through_6",
        model_stage=model_stage,
        audio=audio,
        windows=windows,
        indices=tuple(range(0, 7)),
    )

    direct_by_index = {item["index"]: item for item in direct["focus_windows"]}
    prefix_by_index = {item["index"]: item for item in prefix["focus_windows"]}
    comparisons: list[dict[str, Any]] = []
    any_difference = False
    for index in FOCUS_INDICES:
        left = direct_by_index[index]
        right = prefix_by_index[index]
        transcript_equal = left["transcript"] == right["transcript"]
        repeat_count_equal = left["expected_repeat_count"] == right["expected_repeat_count"]
        same = transcript_equal and repeat_count_equal
        any_difference = any_difference or not same
        comparisons.append(
            {
                "index": index,
                "transcript_equal": transcript_equal,
                "expected_repeat_count_equal": repeat_count_equal,
                "direct_repeat_count": left["expected_repeat_count"],
                "prefix_repeat_count": right["expected_repeat_count"],
                "same": same,
            }
        )

    manifest = {
        "schema_version": 2,
        "record_type": "phase2e_case298_whisper_call_order_diagnostic",
        "case_id": CASE_ID,
        "codec_path": "AMI PCM -> exact pinned FFmpeg AAC MP4 -> product ingest FLAC master -> faster-whisper",
        "ffmpeg_archive_sha256": ffmpeg_archive_sha,
        "master_sha256": _sha256(master),
        "master_duration_seconds": round(duration, 6),
        "model": "large-v3-turbo",
        "window_seconds": WINDOW_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "focus_indices": list(FOCUS_INDICES),
        "arms": [direct, prefix],
        "focus_comparisons": comparisons,
        "call_order_changes_focus_output": any_difference,
        "interpretation": (
            "call_order_or_model_state_affects_focus_windows"
            if any_difference
            else "no_call_order_effect_observed_in_same_run"
        ),
        "safety": {
            "production_code_changed_by_diagnostic": False,
            "product_default_changed": False,
            "detector_or_guard_changed": False,
            "approval_created": False,
            "render_performed": False,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"PHASE2E_CASE298_CALL_ORDER_DIFFERENCE={int(any_difference)}")
    for item in comparisons:
        print(
            f"PHASE2E_CASE298_WINDOW_{item['index']}_SAME={int(item['same'])} "
            f"DIRECT_REPEAT={item['direct_repeat_count']} PREFIX_REPEAT={item['prefix_repeat_count']}"
        )
    print(f"PHASE2E_CASE298_SEQUENCE_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
