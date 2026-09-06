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
    build_transcription_chunk_windows,
    merge_chunked_transcript_segments,
)
from video_tunner.transcription_consensus import (
    REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
    _normalise_token,
    _owner_for_time,
    _phrase_occurrences,
    _repeat_hypotheses,
    _timings_agree,
    merge_chunked_transcript_segments_with_repeat_consensus,
)

CASE_ID = "ami-ts3005d-c-repeat-298"
WINDOW_SECONDS = 12.0
HOP_SECONDS = 3.0
WINDOW_INDICES = (4, 5, 6)
EXPECTED_FFMPEG_ARCHIVE_SHA256 = "87c4729f3193f3ba562bada0330a98338c9a858d25b15fc98338a1364667348b"


def _normalise_phrase(text: str | None) -> tuple[str, ...]:
    if not text:
        return ()
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    result: list[str] = []
    for raw in asciiish.split():
        token = re.sub(r"[^a-z0-9]+", "", raw)
        if token:
            result.append(token)
    return tuple(result)


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


def _hypothesis_dict(item: Any) -> dict[str, Any]:
    return {
        "window_index": item.window_index,
        "phrase": list(item.phrase),
        "first_start": round(float(item.first_start), 6),
        "first_end": round(float(item.first_end), 6),
        "second_start": round(float(item.second_start), 6),
        "second_end": round(float(item.second_end), 6),
        "words": [
            {
                "text": word.text,
                "start": round(float(word.start), 6),
                "end": round(float(word.end), 6),
                "probability": word.probability,
            }
            for word in item.words
        ],
    }


def _transcript_text(segments: tuple[Any, ...]) -> str:
    return " ".join(segment.text for segment in segments if segment.text).strip()


def _candidate_matches(segments: tuple[Any, ...], expected: tuple[str, ...]) -> list[dict[str, Any]]:
    transcript = TranscriptResult(
        language="en",
        language_probability=None,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=segments,
    )
    matches: list[dict[str, Any]] = []
    for candidate in build_semantic_candidates(transcript, mode="conservative"):
        removed = str((candidate.get("evidence") or {}).get("removed_text") or "")
        if candidate.get("kind") != "possible_repetition":
            continue
        if _normalise_phrase(removed) != expected:
            continue
        matches.append(
            {
                "removed_text": removed,
                "start": candidate.get("start"),
                "end": candidate.get("end"),
            }
        )
    return matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--model-stage", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--ffmpeg-archive-sha256", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    supplied_ffmpeg_sha = str(args.ffmpeg_archive_sha256).strip().lower()
    if supplied_ffmpeg_sha != EXPECTED_FFMPEG_ARCHIVE_SHA256:
        raise RuntimeError(
            "Unexpected FFmpeg archive SHA: "
            f"{supplied_ffmpeg_sha} != {EXPECTED_FFMPEG_ARCHIVE_SHA256}"
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
    if not ffmpeg.is_file():
        raise RuntimeError(f"Missing FFmpeg executable: {ffmpeg}")

    clip_wav = output / "source_clip.wav"
    video = output / "aac_video.mp4"
    render_start = float(case["render_clip_start"])
    render_duration = float(case["render_clip_duration"])

    _run(
        [
            str(ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
            "-ss", str(render_start), "-t", str(render_duration), "-i", source_raw,
            "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(clip_wav),
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

    ingest = ingest_video(video, output / "Ingest")
    if ingest.get("status") != "ready":
        raise RuntimeError(f"Embedded ingest did not return ready: {ingest}")
    master = Path(str(ingest["master_audio"]))
    audio = decode_audio(str(master), sampling_rate=WHISPER_SAMPLE_RATE)
    duration = float(len(audio)) / float(WHISPER_SAMPLE_RATE)
    all_windows = build_transcription_chunk_windows(
        duration,
        window_seconds=WINDOW_SECONDS,
        hop_seconds=HOP_SECONDS,
    )
    selected_windows = [window for window in all_windows if window.index in WINDOW_INDICES]
    if tuple(window.index for window in selected_windows) != WINDOW_INDICES:
        raise RuntimeError(
            f"Expected windows {WINDOW_INDICES}, got {[window.index for window in selected_windows]}"
        )

    model = WhisperModel(
        str(Path(args.model_stage).resolve()),
        device="cpu",
        compute_type="int8",
        local_files_only=True,
    )
    chunks: list[tuple[Any, tuple[Any, ...]]] = []
    expected = _normalise_phrase(str(case["reparandum_text"]))
    window_records: list[dict[str, Any]] = []

    for window in selected_windows:
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
        hypotheses = _repeat_hypotheses(window, segments)
        expected_hypotheses = [item for item in hypotheses if item.phrase == expected]
        window_records.append(
            {
                "index": window.index,
                "start": window.start,
                "end": window.end,
                "ownership_start": window.ownership_start,
                "ownership_end": window.ownership_end,
                "transcript": _transcript_text(segments),
                "all_repeat_hypotheses": [_hypothesis_dict(item) for item in hypotheses],
                "expected_repeat_hypotheses": [_hypothesis_dict(item) for item in expected_hypotheses],
                "expected_candidate_matches": _candidate_matches(segments, expected),
            }
        )

    baseline = merge_chunked_transcript_segments(chunks)
    consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
    baseline_words = tuple(word for segment in baseline for word in segment.words)

    left_candidates = [item for item in _repeat_hypotheses(*chunks[0]) if item.phrase == expected]
    owner_candidates = [item for item in _repeat_hypotheses(*chunks[1]) if item.phrase == expected]
    right_candidates = [item for item in _repeat_hypotheses(*chunks[2]) if item.phrase == expected]
    pair_records: list[dict[str, Any]] = []

    for left in left_candidates:
        for right in right_candidates:
            timing_deltas = {
                "first_start": round(abs(left.first_start - right.first_start), 6),
                "first_end": round(abs(left.first_end - right.first_end), 6),
                "second_start": round(abs(left.second_start - right.second_start), 6),
                "second_end": round(abs(left.second_end - right.second_end), 6),
            }
            timing_agree = _timings_agree(
                left,
                right,
                tolerance_seconds=REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
            )
            first_start = (left.first_start + right.first_start) / 2.0
            first_end = (left.first_end + right.first_end) / 2.0
            second_start = (left.second_start + right.second_start) / 2.0
            second_end = (left.second_end + right.second_end) / 2.0
            owner = _owner_for_time(chunks, (first_start + first_end) / 2.0)
            straddles_owner = bool(
                owner
                and min(left.window_index, right.window_index)
                < owner.index
                < max(left.window_index, right.window_index)
            )
            owner_has_repeat = any(
                item.phrase == left.phrase
                and _timings_agree(
                    item,
                    left,
                    tolerance_seconds=REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
                )
                for item in owner_candidates
            )
            interval_start = min(first_start, second_start)
            interval_end = max(first_end, second_end)
            in_interval = tuple(
                sorted(
                    (
                        word
                        for word in baseline_words
                        if interval_start - REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS
                        <= (word.start + word.end) / 2.0
                        <= interval_end + REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS
                    ),
                    key=lambda item: (item.start, item.end, item.text),
                )
            )
            occurrences = _phrase_occurrences(
                in_interval,
                left.phrase,
                start=interval_start,
                end=interval_end,
                tolerance_seconds=REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
            )
            normalised_baseline = tuple(
                token
                for word in in_interval
                if (token := _normalise_token(word.text))
            )
            pair_records.append(
                {
                    "left_window": left.window_index,
                    "right_window": right.window_index,
                    "timing_tolerance_seconds": REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
                    "timing_deltas_seconds": timing_deltas,
                    "timing_agree": timing_agree,
                    "averaged_first_start": round(first_start, 6),
                    "averaged_first_end": round(first_end, 6),
                    "averaged_second_start": round(second_start, 6),
                    "averaged_second_end": round(second_end, 6),
                    "owner_index": None if owner is None else owner.index,
                    "owner_region": None if owner is None else [owner.ownership_start, owner.ownership_end],
                    "supporters_straddle_owner": straddles_owner,
                    "owner_has_matching_repeat": owner_has_repeat,
                    "baseline_interval_words": [
                        {
                            "text": word.text,
                            "start": round(float(word.start), 6),
                            "end": round(float(word.end), 6),
                        }
                        for word in in_interval
                    ],
                    "baseline_normalised_tokens": list(normalised_baseline),
                    "baseline_phrase_occurrence_count": len(occurrences),
                    "baseline_is_exactly_one_phrase": normalised_baseline == left.phrase,
                    "all_current_consensus_checks_pass": bool(
                        timing_agree
                        and straddles_owner
                        and not owner_has_repeat
                        and len(occurrences) == 1
                        and normalised_baseline == left.phrase
                    ),
                }
            )

    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_case298_repeat_consensus_diagnostic",
        "case_id": CASE_ID,
        "codec_path": "AMI PCM -> exact pinned FFmpeg AAC MP4 -> product ingest FLAC master -> Whisper",
        "ffmpeg_archive_sha256": supplied_ffmpeg_sha,
        "model": "large-v3-turbo",
        "window_seconds": WINDOW_SECONDS,
        "hop_seconds": HOP_SECONDS,
        "selected_window_indices": list(WINDOW_INDICES),
        "expected_phrase": list(expected),
        "windows": window_records,
        "supporter_pair_checks": pair_records,
        "baseline_transcript": _transcript_text(baseline),
        "baseline_expected_candidate_matches": _candidate_matches(baseline, expected),
        "consensus_transcript": _transcript_text(consensus),
        "consensus_expected_candidate_matches": _candidate_matches(consensus, expected),
        "consensus_changed_baseline": _transcript_text(consensus) != _transcript_text(baseline),
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
    print(f"PHASE2E_CASE298_LEFT_HYPOTHESES={len(left_candidates)}")
    print(f"PHASE2E_CASE298_OWNER_HYPOTHESES={len(owner_candidates)}")
    print(f"PHASE2E_CASE298_RIGHT_HYPOTHESES={len(right_candidates)}")
    print(f"PHASE2E_CASE298_PAIR_CHECKS={len(pair_records)}")
    print(f"PHASE2E_CASE298_BASELINE_RECOVERS={int(bool(_candidate_matches(baseline, expected)))}")
    print(f"PHASE2E_CASE298_CONSENSUS_RECOVERS={int(bool(_candidate_matches(consensus, expected)))}")
    print(f"PHASE2E_CASE298_MANIFEST={manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
