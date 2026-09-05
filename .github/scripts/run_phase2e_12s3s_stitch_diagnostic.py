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
    TranscriptSegment,
    WordTiming,
    WHISPER_SAMPLE_RATE,
    _normalise_segments,
)

CASE_ID = "ami-es2002b-d-repeat-157"
WINDOW_SECONDS = 12.0
HOP_SECONDS = 3.0
WINDOW_STARTS = (12.0, 15.0, 18.0)
FOCUS_START = 17.0
FOCUS_END = 25.5
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _normalise_phrase(text: str | None) -> str:
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(
        token for raw in asciiish.split() if (token := _TOKEN_RE.sub("", raw))
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


def _transcribe_window(
    model: WhisperModel,
    audio: Any,
    start: float,
) -> tuple[TranscriptSegment, ...]:
    start_sample = int(round(start * WHISPER_SAMPLE_RATE))
    end_sample = int(round((start + WINDOW_SECONDS) * WHISPER_SAMPLE_RATE))
    raw_segments, _ = model.transcribe(
        audio[start_sample:end_sample],
        language="en",
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=True,
    )
    return _normalise_segments(raw_segments)


def _global_words(segments: tuple[TranscriptSegment, ...], start: float) -> list[WordTiming]:
    words: list[WordTiming] = []
    for segment in segments:
        for word in segment.words:
            words.append(
                WordTiming(
                    text=word.text,
                    start=round(start + float(word.start), 6),
                    end=round(start + float(word.end), 6),
                    probability=word.probability,
                )
            )
    return words


def _owner_bounds(start: float) -> tuple[float, float]:
    margin = (WINDOW_SECONDS - HOP_SECONDS) / 2.0
    return start + margin, start + WINDOW_SECONDS - margin


def _focus_words(words: list[WordTiming]) -> list[dict[str, Any]]:
    return [
        {
            "text": word.text,
            "start": round(float(word.start), 6),
            "end": round(float(word.end), 6),
            "midpoint": round((float(word.start) + float(word.end)) / 2.0, 6),
        }
        for word in words
        if float(word.end) >= FOCUS_START and float(word.start) <= FOCUS_END
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    case = next(item for item in fixture.get("cases") or [] if item.get("id") == CASE_ID)
    source_id = str(case["audio_source_id"])
    source_raw = os.environ.get(_source_env_name(source_id))
    if not source_raw or not Path(source_raw).is_file():
        raise RuntimeError(f"Missing AMI source: {source_id}")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    clip_wav = output / "source_clip.wav"
    video = output / "aac_video.mp4"
    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])
    ffmpeg = Path(args.ffmpeg)

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
    if ingest.get("status") not in {"ready", "ready_auto", "ready_manual"}:
        raise RuntimeError(f"Ingest did not produce ready master: {ingest}")
    master = Path(str(ingest["master_audio"]))
    audio = decode_audio(str(master), sampling_rate=WHISPER_SAMPLE_RATE)
    model = WhisperModel(
        str(Path(args.model_stage).resolve()),
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )

    windows: list[dict[str, Any]] = []
    selected_words: list[WordTiming] = []
    expected = _normalise_phrase(str(case["reparandum_text"]))
    for start in WINDOW_STARTS:
        segments = _transcribe_window(model, audio, start)
        words = _global_words(segments, start)
        owner_start, owner_end = _owner_bounds(start)
        owned = [
            word for word in words
            if owner_start <= (float(word.start) + float(word.end)) / 2.0 < owner_end
        ]
        selected_words.extend(owned)
        transcript = TranscriptResult(
            language="en",
            language_probability=None,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=segments,
        )
        local_matches = []
        for candidate in build_semantic_candidates(transcript, mode="conservative"):
            removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
            if candidate.get("kind") == case.get("expected_candidate_kind") and _normalise_phrase(removed) == expected:
                local_matches.append({
                    "removed_text": removed,
                    "global_start": round(start + float(candidate["start"]), 6),
                    "global_end": round(start + float(candidate["end"]), 6),
                })
        windows.append({
            "start": start,
            "end": start + WINDOW_SECONDS,
            "owner_start": owner_start,
            "owner_end": owner_end,
            "transcript": " ".join(segment.text for segment in segments if segment.text).strip(),
            "expected_candidate_matches": local_matches,
            "focus_words": _focus_words(words),
            "owned_focus_words": _focus_words(owned),
        })

    selected_words.sort(key=lambda word: (float(word.start), float(word.end)))
    merged_segment = TranscriptSegment(
        text=" ".join(word.text for word in selected_words).strip(),
        start=float(selected_words[0].start),
        end=float(selected_words[-1].end),
        words=tuple(selected_words),
    )
    merged_transcript = TranscriptResult(
        language="en",
        language_probability=None,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(merged_segment,),
    )
    merged_matches = []
    for candidate in build_semantic_candidates(merged_transcript, mode="conservative"):
        removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
        if candidate.get("kind") == case.get("expected_candidate_kind") and _normalise_phrase(removed) == expected:
            merged_matches.append({
                "removed_text": removed,
                "start": candidate.get("start"),
                "end": candidate.get("end"),
            })

    center = next(item for item in windows if item["start"] == 15.0)
    center_recovers = len(center["expected_candidate_matches"]) == 1
    local_owner_merge_recovers = len(merged_matches) == 1
    diagnosis = (
        "ownership_merge_drops_or_corrupts_center_hypothesis"
        if center_recovers and not local_owner_merge_recovers
        else "owner_merge_preserves_candidate"
        if center_recovers and local_owner_merge_recovers
        else "center_hypothesis_not_recovered"
    )
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_12s3s_stitch_diagnostic",
        "case_id": CASE_ID,
        "codec_path": "AMI PCM -> AAC MP4 -> product ingest master -> Whisper",
        "window_seconds": WINDOW_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "windows": windows,
        "merged_focus_words": _focus_words(selected_words),
        "merged_expected_candidate_matches": merged_matches,
        "center_recovers": center_recovers,
        "local_owner_merge_recovers": local_owner_merge_recovers,
        "diagnosis": diagnosis,
        "safety": {
            "production_merge_changed": False,
            "product_default_changed": False,
            "detector_or_guard_changed": False,
            "approval_created": False,
            "render_performed": False,
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PHASE2E_12S3S_STITCH_CENTER_RECOVERS={int(center_recovers)}")
    print(f"PHASE2E_12S3S_STITCH_OWNER_MERGE_RECOVERS={int(local_owner_merge_recovers)}")
    print(f"PHASE2E_12S3S_STITCH_DIAGNOSIS={diagnosis}")
    print(f"PHASE2E_12S3S_STITCH_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
