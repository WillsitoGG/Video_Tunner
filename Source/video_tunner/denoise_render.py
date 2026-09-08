from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from .approval import sha256_path
from .denoise_execution_authorization import validate_denoise_execution_authorization
from .denoise_runtime import (
    DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
    DenoiserRuntimeError,
    deepfilter_executable_path,
    validate_selected_denoiser_binary,
)
from .media import probe_media
from .tools import resolve_tool


DENOISE_RENDER_SCHEMA_VERSION = 1
DENOISE_RENDER_RECORD_TYPE = "denoise_render_result"
DENOISE_RENDER_AUDIO_CODEC = "aac"
DENOISE_RENDER_AUDIO_BITRATE = "192k"


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _probe_source_audio_contract(source: Path) -> dict[str, Any]:
    ffprobe = resolve_tool("ffprobe")
    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=channels,sample_rate",
            "-of",
            "json",
            str(source),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe no pudo inspeccionar el audio source: {completed.stderr}")
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams")
    if not isinstance(streams, list) or len(streams) != 1 or not isinstance(streams[0], dict):
        raise ValueError("No se pudo acreditar exactamente el primer stream de audio.")
    try:
        channels = int(streams[0].get("channels"))
        sample_rate_hz = int(streams[0].get("sample_rate"))
    except (TypeError, ValueError) as exc:
        raise ValueError("ffprobe no devolvió channels/sample_rate válidos.") from exc
    if channels <= 0 or sample_rate_hz <= 0:
        raise ValueError("Audio source contiene channels/sample_rate no positivos.")
    return {"channels": channels, "sample_rate_hz": sample_rate_hz}


def _read_pcm16_mono_48k(path: Path) -> tuple[wave._wave_params, bytes, int]:
    with wave.open(str(path), "rb") as wav:
        params = wav.getparams()
        if wav.getnchannels() != 1:
            raise ValueError(f"{path.name}: se requiere audio mono.")
        if wav.getsampwidth() != 2:
            raise ValueError(f"{path.name}: se requiere PCM16.")
        if wav.getframerate() != 48000:
            raise ValueError(f"{path.name}: se requiere 48 kHz.")
        frames = int(wav.getnframes())
        raw = wav.readframes(frames)
    if len(raw) != frames * 2:
        raise ValueError(f"{path.name}: bytes PCM no coinciden con frame count.")
    return params, raw, frames


def normalize_denoised_pcm_timeline(
    input_wav: str | Path,
    denoised_wav: str | Path,
    destination_wav: str | Path,
    *,
    max_abs_delta_seconds: float = DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
) -> dict[str, Any]:
    """Normalize only the right tail after compensated DeepFilterNet processing.

    No alignment search, time shift or level matching is permitted. The raw
    duration delta must already satisfy the frozen 3.6g tolerance. Only a tail
    trim or digital-silence tail pad may make the decoded PCM frame count exact.
    """
    input_path = Path(input_wav).resolve()
    candidate_path = Path(denoised_wav).resolve()
    output_path = Path(destination_wav).resolve()
    input_params, input_raw, input_frames = _read_pcm16_mono_48k(input_path)
    _, candidate_raw, candidate_frames = _read_pcm16_mono_48k(candidate_path)

    raw_frame_delta = candidate_frames - input_frames
    raw_duration_delta_seconds = raw_frame_delta / 48000.0
    if abs(raw_duration_delta_seconds) > float(max_abs_delta_seconds) + 1e-12:
        raise ValueError(
            "DeepFilterNet raw duration delta supera el contrato 3.6g: "
            f"{raw_duration_delta_seconds:.9f}s > {float(max_abs_delta_seconds):.9f}s."
        )

    if raw_frame_delta > 0:
        final_raw = candidate_raw[: input_frames * 2]
        action = "trim_right_tail"
    elif raw_frame_delta < 0:
        final_raw = candidate_raw + (b"\x00\x00" * (-raw_frame_delta))
        action = "pad_right_tail_silence"
    else:
        final_raw = candidate_raw
        action = "none"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(48000)
        wav.writeframes(final_raw)

    _, normalized_raw, final_frames = _read_pcm16_mono_48k(output_path)
    if final_frames != input_frames:
        raise RuntimeError("La normalización temporal de cola no produjo frame count exacto.")
    prefix_bytes = min(len(candidate_raw), len(normalized_raw))
    if normalized_raw[:prefix_bytes] != candidate_raw[:prefix_bytes]:
        raise RuntimeError("La normalización temporal alteró muestras antes de la cola derecha.")

    return {
        "input_frames": input_frames,
        "raw_output_frames": candidate_frames,
        "raw_frame_delta": raw_frame_delta,
        "raw_duration_delta_seconds": round(raw_duration_delta_seconds, 9),
        "max_abs_raw_duration_delta_seconds": float(max_abs_delta_seconds),
        "timeline_normalization_action": action,
        "final_frames": final_frames,
        "alignment_search_performed": False,
        "time_shift_performed": False,
        "level_matching_performed": False,
    }


def validate_denoise_render_request(
    source: str | Path,
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    plan_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    """Revalidate the complete 3.6a-h chain immediately before DeepFilterNet."""
    base = {
        "valid": False,
        "render_authorized": False,
        "product_default": "preserve",
        "auto_apply": False,
    }
    authorization_digest = str(authorization_sha256 or "").strip().lower()
    if not _valid_sha256(authorization_digest):
        return base | {"status": "blocked_invalid_authorization_sha", "reason": "authorization_sha256_invalid"}

    source_path = Path(source).resolve()
    if not source_path.is_file():
        return base | {"status": "blocked_source_mismatch", "reason": "source_not_found"}
    actual_source_sha = sha256_path(source_path)

    validation = validate_denoise_execution_authorization(
        noise_audit,
        selection_review,
        plan,
        authorization,
        noise_audit_sha256=noise_audit_sha256,
        selection_review_sha256=selection_review_sha256,
        plan_sha256=plan_sha256,
        current_output_sha256=actual_source_sha,
    )
    if validation.get("status") != "valid_authorized" or not validation.get("denoise_render_authorization"):
        return base | {
            "status": "blocked_execution_authorization",
            "reason": validation.get("reason") or "denoise_render_authorization_not_present",
            "authorization_status": validation.get("status"),
        }

    bindings = plan.get("bindings")
    if not isinstance(bindings, dict):
        return base | {"status": "blocked_invalid_plan", "reason": "plan_bindings_missing"}
    expected_source_sha = str(bindings.get("quality_output_sha256") or "").strip().lower()
    if actual_source_sha != expected_source_sha or validation.get("quality_output_sha256") != actual_source_sha:
        return base | {
            "status": "blocked_source_mismatch",
            "reason": "quality_output_sha256_changed",
            "actual_source_sha256": actual_source_sha,
            "expected_source_sha256": expected_source_sha,
        }

    media = probe_media(source_path)
    if media.get("video_streams") != 1 or media.get("audio_streams") != 1:
        return base | {
            "status": "blocked_media_layout",
            "reason": "denoise_renderer_requires_exactly_one_video_and_one_audio_stream",
            "video_streams": media.get("video_streams"),
            "audio_streams": media.get("audio_streams"),
        }
    try:
        source_audio = _probe_source_audio_contract(source_path)
    except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
        return base | {"status": "blocked_media_layout", "reason": str(exc)}
    if source_audio["channels"] != 1:
        return base | {
            "status": "blocked_media_layout",
            "reason": "phase3_6i_foundation_requires_mono_source_audio",
            "audio_channels": source_audio["channels"],
        }

    try:
        runtime_validation = validate_selected_denoiser_binary(probe_cli=True)
    except (DenoiserRuntimeError, OSError, ValueError) as exc:
        return base | {"status": "blocked_runtime_contract", "reason": str(exc)}

    return base | {
        "status": "valid_denoise_render_request",
        "reason": None,
        "valid": True,
        "render_authorized": True,
        "source_sha256": actual_source_sha,
        "source_media": media,
        "source_audio": source_audio,
        "authorization_sha256": authorization_digest,
        "selected_candidate_id": validation.get("selected_candidate_id"),
        "runtime_contract_fingerprint": validation.get("runtime_contract_fingerprint"),
        "runtime_validation": {
            "valid": True,
            "candidate_id": runtime_validation["candidate_id"],
            "version": runtime_validation["version"],
            "asset_sha256": runtime_validation["asset_sha256"],
            "asset_size_bytes": runtime_validation["asset_size_bytes"],
            "cli_contract_pass": bool(runtime_validation.get("cli_contract_pass")),
        },
    }


def _run_checked(command: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} falló con código {completed.returncode}:\n"
            f"stdout={completed.stdout[-3000:]}\n"
            f"stderr={completed.stderr[-3000:]}"
        )
    return completed


def render_denoised_media(
    source: str | Path,
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    destination: str | Path,
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    plan_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    """Render one explicitly authorized DeepFilterNet treatment as a derived file.

    Phase 3.6i is a technical renderer foundation. A successful render result is
    deliberately not a technical or human PASS; independent post-render and
    perceptual gates remain mandatory before this path can be generalized.
    """
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()
    if source_path == destination_path:
        raise ValueError("El source acreditado nunca puede sobrescribirse.")

    validation = validate_denoise_render_request(
        source_path,
        noise_audit,
        selection_review,
        plan,
        authorization,
        noise_audit_sha256=noise_audit_sha256,
        selection_review_sha256=selection_review_sha256,
        plan_sha256=plan_sha256,
        authorization_sha256=authorization_sha256,
    )
    if validation.get("status") != "valid_denoise_render_request":
        raise ValueError(
            "Denoise render gate bloqueado: "
            f"{validation.get('status')} ({validation.get('reason')})"
        )

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    deepfilter = deepfilter_executable_path()

    with tempfile.TemporaryDirectory(prefix="video_tunner_denoise_render_") as temporary:
        temp = Path(temporary)
        input_wav = temp / "input_pcm16_mono_48k.wav"
        raw_dir = temp / "deepfilter_raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        decoded_wav = temp / "deepfilter_decoded_pcm16_mono_48k.wav"
        normalized_wav = temp / "deepfilter_timeline_normalized.wav"

        _run_checked(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-map",
                "0:a:0",
                "-vn",
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s16le",
                str(input_wav),
            ],
            label="FFmpeg PCM extraction",
        )
        _read_pcm16_mono_48k(input_wav)

        _run_checked(
            [
                str(deepfilter),
                "--compensate-delay",
                "--output-dir",
                str(raw_dir),
                str(input_wav),
            ],
            label="DeepFilterNet",
        )
        raw_outputs = sorted(raw_dir.glob("*.wav"))
        if len(raw_outputs) != 1:
            raise RuntimeError(f"DeepFilterNet produjo {len(raw_outputs)} WAVs; se esperaba exactamente 1.")

        _run_checked(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(raw_outputs[0]),
                "-ac",
                "1",
                "-ar",
                "48000",
                "-c:a",
                "pcm_s16le",
                str(decoded_wav),
            ],
            label="FFmpeg DeepFilterNet decode",
        )
        timeline = normalize_denoised_pcm_timeline(input_wav, decoded_wav, normalized_wav)

        _run_checked(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-i",
                str(normalized_wav),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-map_metadata",
                "0",
                "-c:v",
                "copy",
                "-c:a",
                DENOISE_RENDER_AUDIO_CODEC,
                "-b:a",
                DENOISE_RENDER_AUDIO_BITRATE,
                str(destination_path),
            ],
            label="FFmpeg denoise remux",
        )

    if not destination_path.is_file():
        raise RuntimeError("El renderer terminó sin crear el output denoised.")
    source_sha_after = sha256_path(source_path)
    if source_sha_after != validation["source_sha256"]:
        destination_path.unlink(missing_ok=True)
        raise RuntimeError("El source cambió durante el render; output invalidado.")

    output_media = probe_media(destination_path)
    return {
        "schema_version": DENOISE_RENDER_SCHEMA_VERSION,
        "record_type": DENOISE_RENDER_RECORD_TYPE,
        "status": "denoise_render_complete",
        "source": {
            "file": source_path.name,
            "sha256": source_sha_after,
            "media": validation["source_media"],
            "audio": validation["source_audio"],
        },
        "output": {
            "file": destination_path.name,
            "sha256": sha256_path(destination_path),
            "media": output_media,
        },
        "bindings": {
            "noise_audit_sha256": str(noise_audit_sha256).strip().lower(),
            "selection_review_sha256": str(selection_review_sha256).strip().lower(),
            "plan_sha256": str(plan_sha256).strip().lower(),
            "authorization_sha256": str(authorization_sha256).strip().lower(),
            "selected_candidate_id": validation["selected_candidate_id"],
            "runtime_contract_fingerprint": validation["runtime_contract_fingerprint"],
        },
        "runtime": validation["runtime_validation"],
        "timeline": timeline,
        "video_policy": "stream_copy_first_and_only_video_stream",
        "audio_policy": "deepfilternet_compensated_pcm16_mono_48k_then_aac_192k",
        "source_overwritten": False,
        "technical_post_render_verification_required": True,
        "human_perceptual_review_required": True,
        "technical_pass": False,
        "human_pass": False,
        "product_default": "preserve",
        "auto_apply": False,
    }


def save_denoise_render_result(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
