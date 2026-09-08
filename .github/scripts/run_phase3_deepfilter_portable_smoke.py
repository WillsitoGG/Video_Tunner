from __future__ import annotations

import argparse
import json
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path

from video_tunner.denoise_runtime import (
    DEEPFILTER_INPUT_SAMPLE_RATE_HZ,
    DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
    validate_selected_denoiser_binary,
)


def write_input(path: Path, seconds: float = 3.0) -> int:
    sample_rate = DEEPFILTER_INPUT_SAMPLE_RATE_HZ
    frame_count = int(round(seconds * sample_rate))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for index in range(frame_count):
            t = index / sample_rate
            speech_like = 0.22 * math.sin(2.0 * math.pi * 180.0 * t)
            harmonic = 0.08 * math.sin(2.0 * math.pi * 360.0 * t)
            deterministic_noise = 0.035 * math.sin(2.0 * math.pi * 3173.0 * t)
            value = max(-0.95, min(0.95, speech_like + harmonic + deterministic_noise))
            frames += struct.pack("<h", int(round(value * 32767.0)))
        wav.writeframes(frames)
    return frame_count


def inspect_wav(path: Path) -> dict[str, float | int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
    return {
        "channels": channels,
        "sample_width_bytes": sample_width,
        "sample_rate_hz": sample_rate,
        "frames": frames,
        "duration_seconds": frames / float(sample_rate),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    executable = Path(args.exe).resolve()
    work = Path(args.work_dir).resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    binary_validation = validate_selected_denoiser_binary(executable, probe_cli=True)
    source = work / "input.wav"
    output_dir = work / "output"
    output_dir.mkdir()
    input_frames = write_input(source)

    completed = subprocess.run(
        [
            str(executable),
            "--compensate-delay",
            "--output-dir",
            str(output_dir),
            str(source),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"DeepFilterNet offline smoke failed ({completed.returncode}). "
            f"stdout={completed.stdout[-2000:]} stderr={completed.stderr[-2000:]}"
        )

    outputs = sorted(output_dir.glob("*.wav"))
    if len(outputs) != 1:
        raise RuntimeError(f"DeepFilterNet produced {len(outputs)} WAV outputs; expected exactly one.")

    media = inspect_wav(outputs[0])
    if media["channels"] != 1 or media["sample_width_bytes"] != 2:
        raise RuntimeError(f"Unexpected DeepFilterNet PCM contract: {media}")
    if media["sample_rate_hz"] != DEEPFILTER_INPUT_SAMPLE_RATE_HZ:
        raise RuntimeError(f"Unexpected DeepFilterNet sample rate: {media}")

    input_duration = input_frames / float(DEEPFILTER_INPUT_SAMPLE_RATE_HZ)
    delta = float(media["duration_seconds"]) - input_duration
    if abs(delta) > DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS + 1e-12:
        raise RuntimeError(
            f"DeepFilterNet raw duration delta {delta:.9f}s exceeds "
            f"{DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS:.9f}s."
        )

    result = {
        "schema_version": 1,
        "record_type": "phase3_deepfilter_portable_offline_smoke",
        "status": "PASS",
        "binary": binary_validation,
        "input": {
            "pcm": "pcm_s16le",
            "channels": 1,
            "sample_rate_hz": DEEPFILTER_INPUT_SAMPLE_RATE_HZ,
            "duration_seconds": input_duration,
        },
        "output": media,
        "raw_duration_delta_seconds": round(delta, 8),
        "max_abs_raw_duration_delta_seconds": DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
        "network_requirement": "outbound_blocked_by_workflow_for_exact_executable",
        "path_resolution": "exact_bundled_path_only",
        "runtime_download_performed": False,
        "denoise_authorized": False,
        "renderer_authorized": False,
        "auto_apply": False,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
