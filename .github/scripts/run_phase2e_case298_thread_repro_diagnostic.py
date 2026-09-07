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
from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import (
    TranscriptResult,
    WHISPER_SAMPLE_RATE,
    _normalise_segments,
    build_transcription_chunk_windows,
)
from video_tunner.transcription_consensus import (
    _repeat_hypotheses,
    merge_chunked_transcript_segments_with_repeat_consensus,
)

CASE_ID = "ami-ts3005d-c-repeat-298"
WINDOW_SECONDS = 12.0
HOP_SECONDS = 3.0
FOCUS_INDICES = (4, 5, 6)
EXPECTED_PHRASE = ("and", "then", "you", "can")
EXPECTED_FFMPEG_ARCHIVE_SHA256 = "87c4729f3193f3ba562bada0330a98338c9a858d25b15fc98338a1364667348b"
RUNS_PER_ARM = 3


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


def _transcribe_focus(
    *,
    model_stage: Path,
    audio: Any,
    windows: tuple[Any, ...],
    cpu_threads: int,
    run_index: int,
) -> dict[str, Any]:
    model = WhisperModel(
        str(model_stage),
        device="cpu",
        compute_type="int8",
        cpu_threads=cpu_threads,
        num_workers=1,
        local_files_only=True,
    )
    chunks = []
    window_records = []
    for index in FOCUS_INDICES:
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
        chunks.append((window, segments))
        hypotheses = [
            item for item in _repeat_hypotheses(window, segments)
            if item.phrase == EXPECTED_PHRASE
        ]
        window_records.append(
            {
                "index": index,
                "transcript": " ".join(segment.text for segment in segments if segment.text).strip(),
                "expected_repeat_count": len(hypotheses),
                "expected_repeats": [
                    {
                        "first_start": round(float(item.first_start), 6),
                        "first_end": round(float(item.first_end), 6),
                        "second_start": round(float(item.second_start), 6),
                        "second_end": round(float(item.second_end), 6),
                    }
                    for item in hypotheses
                ],
            }
        )

    merged = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
    transcript = TranscriptResult(
        language="en",
        language_probability=None,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=merged,
    )
    candidates = build_semantic_candidates(transcript, mode="conservative")
    expected_candidates = [
        item for item in candidates
        if item.get("kind") == "possible_repetition"
        and tuple(
            re.sub(r"[^a-z0-9]+", "", token.lower())
            for token in str((item.get("evidence") or {}).get("removed_text") or "").split()
            if re.sub(r"[^a-z0-9]+", "", token.lower())
        ) == EXPECTED_PHRASE
    ]
    merged_words = [word.text for segment in merged for word in segment.words]
    signature = {
        "window_repeat_counts": [item["expected_repeat_count"] for item in window_records],
        "merged_words": merged_words,
        "expected_candidate_count": len(expected_candidates),
    }
    del model
    gc.collect()
    return {
        "run_index": run_index,
        "cpu_threads": cpu_threads,
        "num_workers": 1,
        "windows": window_records,
        "merged_text": " ".join(merged_words),
        "expected_candidate_count": len(expected_candidates),
        "signature": signature,
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
        raise RuntimeError("Unexpected FFmpeg archive SHA")

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
    model_stage = Path(args.model_stage).resolve()

    arms = []
    for name, cpu_threads in (("runtime_default_threads", 0), ("serial_cpu_threads_1", 1)):
        runs = [
            _transcribe_focus(
                model_stage=model_stage,
                audio=audio,
                windows=windows,
                cpu_threads=cpu_threads,
                run_index=index + 1,
            )
            for index in range(RUNS_PER_ARM)
        ]
        signatures = [json.dumps(run["signature"], sort_keys=True) for run in runs]
        arms.append(
            {
                "name": name,
                "cpu_threads": cpu_threads,
                "num_workers": 1,
                "runs": runs,
                "unique_signature_count": len(set(signatures)),
                "all_runs_same": len(set(signatures)) == 1,
                "candidate_success_count": sum(run["expected_candidate_count"] == 1 for run in runs),
            }
        )

    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_case298_cpu_thread_reproducibility_diagnostic",
        "case_id": CASE_ID,
        "codec_path": "AMI PCM -> exact pinned FFmpeg AAC MP4 -> product ingest FLAC master -> faster-whisper",
        "ffmpeg_archive_sha256": ffmpeg_archive_sha,
        "master_sha256": _sha256(master),
        "master_duration_seconds": round(duration, 6),
        "model": "large-v3-turbo",
        "window_seconds": WINDOW_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "focus_indices": list(FOCUS_INDICES),
        "runs_per_arm": RUNS_PER_ARM,
        "arms": arms,
        "safety": {
            "production_code_changed_by_diagnostic": False,
            "product_default_changed": False,
            "timing_tolerance_changed": False,
            "detector_or_guard_changed": False,
            "approval_created": False,
            "render_performed": False,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for arm in arms:
        print(
            f"PHASE2E_CASE298_REPRO_ARM={arm['name']} "
            f"UNIQUE_SIGNATURES={arm['unique_signature_count']} "
            f"CANDIDATE_SUCCESS={arm['candidate_success_count']}/{RUNS_PER_ARM}"
        )
    print(f"PHASE2E_CASE298_REPRO_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
