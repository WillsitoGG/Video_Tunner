from __future__ import annotations

import json
import re
import subprocess
import tempfile
import wave
from pathlib import Path
from typing import Any

from .approval import sha256_path
from .denoise_render import (
    DENOISE_RENDER_AUDIO_CODEC,
    DENOISE_RENDER_RECORD_TYPE,
    DENOISE_RENDER_SCHEMA_VERSION,
    validate_denoise_render_request,
)
from .denoise_runtime import DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS
from .media import probe_media
from .tools import resolve_tool


DENOISE_POST_RENDER_SCHEMA_VERSION = 1
DENOISE_POST_RENDER_RECORD_TYPE = "denoise_post_render_verification"
DENOISE_VERIFICATION_SAMPLE_RATE_HZ = 48000
DENOISE_VERIFICATION_CHANNELS = 1

_HASH_LINE = re.compile(r"SHA256=([0-9a-fA-F]{64})")
_ALLOWED_TIMELINE_ACTIONS = {"none", "trim_right_tail", "pad_right_tail_silence"}


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _invalid(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": DENOISE_POST_RENDER_SCHEMA_VERSION,
        "record_type": DENOISE_POST_RENDER_RECORD_TYPE,
        "status": "invalid_evidence",
        "valid_evidence": False,
        "technical_pass": False,
        "human_perceptual_review_required": True,
        "human_pass": False,
        "blockers": [{"code": reason, "class": "invalid_evidence"}],
        "product_default": "preserve",
        "auto_apply": False,
    } | extra


def decoded_video_sha256(source: str | Path) -> str:
    """Hash decoded video frames so an audio-only denoise render cannot alter picture content."""
    path = Path(source).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe el media para video hash: {path}")
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-an",
            "-sn",
            "-dn",
            "-c:v",
            "rawvideo",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo calcular hash de vídeo decodificado:\n{completed.stderr}")
    match = _HASH_LINE.search(completed.stdout or "")
    if not match:
        raise ValueError("FFmpeg hash muxer no devolvió SHA256 de vídeo.")
    return match.group(1).lower()


def _probe_audio_stream_contract(source: str | Path) -> dict[str, Any]:
    path = Path(source).resolve()
    ffprobe = resolve_tool("ffprobe")
    completed = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_name,channels,sample_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ffprobe no pudo inspeccionar el audio: {completed.stderr}")
    payload = json.loads(completed.stdout or "{}")
    streams = payload.get("streams")
    if not isinstance(streams, list) or len(streams) != 1 or not isinstance(streams[0], dict):
        raise ValueError("No se pudo acreditar exactamente el primer stream de audio.")
    stream = streams[0]
    try:
        channels = int(stream.get("channels"))
        sample_rate_hz = int(stream.get("sample_rate"))
    except (TypeError, ValueError) as exc:
        raise ValueError("ffprobe no devolvió channels/sample_rate válidos.") from exc
    codec_name = str(stream.get("codec_name") or "").strip().lower()
    if channels <= 0 or sample_rate_hz <= 0 or not codec_name:
        raise ValueError("Audio stream contract incompleto o no positivo.")
    return {
        "codec_name": codec_name,
        "channels": channels,
        "sample_rate_hz": sample_rate_hz,
    }


def decoded_audio_frame_count_48k_mono(source: str | Path) -> int:
    """Independently decode the full first audio stream to PCM16 mono 48 kHz and count frames."""
    path = Path(source).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"No existe el media para audio frame count: {path}")
    ffmpeg = resolve_tool("ffmpeg")
    with tempfile.TemporaryDirectory(prefix="video_tunner_denoise_verify_") as temporary:
        decoded = Path(temporary) / "decoded_pcm16_mono_48k.wav"
        completed = subprocess.run(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(path),
                "-map",
                "0:a:0",
                "-vn",
                "-ac",
                str(DENOISE_VERIFICATION_CHANNELS),
                "-ar",
                str(DENOISE_VERIFICATION_SAMPLE_RATE_HZ),
                "-c:a",
                "pcm_s16le",
                str(decoded),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"FFmpeg no pudo decodificar audio para verificación:\n{completed.stderr}")
        with wave.open(str(decoded), "rb") as wav:
            if wav.getnchannels() != DENOISE_VERIFICATION_CHANNELS:
                raise ValueError("Decode de verificación no produjo audio mono.")
            if wav.getsampwidth() != 2:
                raise ValueError("Decode de verificación no produjo PCM16.")
            if wav.getframerate() != DENOISE_VERIFICATION_SAMPLE_RATE_HZ:
                raise ValueError("Decode de verificación no produjo 48 kHz.")
            frames = int(wav.getnframes())
    if frames <= 0:
        raise ValueError("Decode de verificación produjo cero frames.")
    return frames


def _validate_reported_timeline(timeline: Any) -> str | None:
    if not isinstance(timeline, dict):
        return "render_result_timeline_missing"
    required_ints = ("input_frames", "raw_output_frames", "raw_frame_delta", "final_frames")
    parsed: dict[str, int] = {}
    for key in required_ints:
        value = timeline.get(key)
        if isinstance(value, bool):
            return "render_result_timeline_invalid_integer"
        try:
            parsed[key] = int(value)
        except (TypeError, ValueError):
            return "render_result_timeline_invalid_integer"
        if parsed[key] != value:
            return "render_result_timeline_invalid_integer"
    if parsed["input_frames"] <= 0 or parsed["raw_output_frames"] <= 0 or parsed["final_frames"] <= 0:
        return "render_result_timeline_nonpositive_frames"
    if parsed["raw_frame_delta"] != parsed["raw_output_frames"] - parsed["input_frames"]:
        return "render_result_timeline_raw_frame_delta_inconsistent"

    try:
        raw_delta_seconds = float(timeline.get("raw_duration_delta_seconds"))
        max_abs_delta = float(timeline.get("max_abs_raw_duration_delta_seconds"))
    except (TypeError, ValueError):
        return "render_result_timeline_invalid_duration"
    expected_delta = parsed["raw_frame_delta"] / float(DENOISE_VERIFICATION_SAMPLE_RATE_HZ)
    if abs(raw_delta_seconds - expected_delta) > 1e-9:
        return "render_result_timeline_raw_duration_inconsistent"
    if abs(max_abs_delta - DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS) > 1e-12:
        return "render_result_timeline_limit_changed"
    if abs(raw_delta_seconds) > DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS + 1e-12:
        return "render_result_timeline_raw_duration_exceeded"
    if parsed["final_frames"] != parsed["input_frames"]:
        return "render_result_timeline_final_frames_not_exact"

    action = timeline.get("timeline_normalization_action")
    if action not in _ALLOWED_TIMELINE_ACTIONS:
        return "render_result_timeline_action_invalid"
    if parsed["raw_frame_delta"] > 0 and action != "trim_right_tail":
        return "render_result_timeline_action_inconsistent"
    if parsed["raw_frame_delta"] < 0 and action != "pad_right_tail_silence":
        return "render_result_timeline_action_inconsistent"
    if parsed["raw_frame_delta"] == 0 and action != "none":
        return "render_result_timeline_action_inconsistent"
    for forbidden_flag in (
        "alignment_search_performed",
        "time_shift_performed",
        "level_matching_performed",
    ):
        if timeline.get(forbidden_flag) is not False:
            return f"render_result_{forbidden_flag}_not_false"
    return None


def build_denoise_post_render_verification(
    source: str | Path,
    output: str | Path,
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    render_result: dict[str, Any],
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    plan_sha256: str,
    authorization_sha256: str,
    render_result_sha256: str,
) -> dict[str, Any]:
    """Independently verify one completed denoise render.

    This gate verifies current provenance, picture preservation, output audio
    contract and decoded timeline. It deliberately does not introduce SNR,
    STOI, SI-SDR, loudness or perceptual thresholds. A technical PASS still
    requires later human perceptual review before denoise can be generalized.
    """
    source_path = Path(source).resolve()
    output_path = Path(output).resolve()
    render_digest = str(render_result_sha256 or "").strip().lower()
    if not _valid_sha256(render_digest):
        return _invalid("invalid_render_result_sha256")
    if source_path == output_path:
        return _invalid("source_output_same_path")
    if not source_path.is_file() or not output_path.is_file():
        return _invalid("source_or_output_missing")

    request = validate_denoise_render_request(
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
    if request.get("status") != "valid_denoise_render_request":
        return _invalid(
            "stale_or_invalid_denoise_chain",
            upstream_status=request.get("status"),
            upstream_reason=request.get("reason"),
        )

    if not isinstance(render_result, dict):
        return _invalid("render_result_not_object")
    if render_result.get("schema_version") != DENOISE_RENDER_SCHEMA_VERSION:
        return _invalid("unsupported_render_result_schema")
    if render_result.get("record_type") != DENOISE_RENDER_RECORD_TYPE:
        return _invalid("invalid_render_result_type")
    if render_result.get("status") != "denoise_render_complete":
        return _invalid("render_result_not_complete")
    if render_result.get("technical_pass") or render_result.get("human_pass") or render_result.get("auto_apply"):
        return _invalid("render_result_contains_premature_pass_or_auto_apply")
    if not render_result.get("technical_post_render_verification_required"):
        return _invalid("render_result_bypasses_technical_verification")
    if not render_result.get("human_perceptual_review_required"):
        return _invalid("render_result_bypasses_human_review")
    if render_result.get("source_overwritten") is not False:
        return _invalid("render_result_source_overwrite_flag_invalid")
    if render_result.get("product_default") != "preserve":
        return _invalid("render_result_product_default_changed")

    expected_bindings = {
        "noise_audit_sha256": str(noise_audit_sha256).strip().lower(),
        "selection_review_sha256": str(selection_review_sha256).strip().lower(),
        "plan_sha256": str(plan_sha256).strip().lower(),
        "authorization_sha256": str(authorization_sha256).strip().lower(),
        "selected_candidate_id": request.get("selected_candidate_id"),
        "runtime_contract_fingerprint": request.get("runtime_contract_fingerprint"),
    }
    if render_result.get("bindings") != expected_bindings:
        return _invalid("render_result_bindings_changed")
    if render_result.get("runtime") != request.get("runtime_validation"):
        return _invalid("render_result_runtime_snapshot_changed")
    if render_result.get("video_policy") != "stream_copy_first_and_only_video_stream":
        return _invalid("render_result_video_policy_changed")
    if render_result.get("audio_policy") != "deepfilternet_compensated_pcm16_mono_48k_then_aac_192k":
        return _invalid("render_result_audio_policy_changed")

    timeline_reason = _validate_reported_timeline(render_result.get("timeline"))
    if timeline_reason is not None:
        return _invalid(timeline_reason)

    actual_source_sha = sha256_path(source_path)
    actual_output_sha = sha256_path(output_path)
    source_record = render_result.get("source")
    output_record = render_result.get("output")
    if not isinstance(source_record, dict) or not isinstance(output_record, dict):
        return _invalid("render_result_source_output_provenance_missing")
    if source_record.get("sha256") != actual_source_sha:
        return _invalid("render_result_source_sha_changed")
    if output_record.get("sha256") != actual_output_sha:
        return _invalid("render_result_output_sha_changed")
    if actual_source_sha != request.get("source_sha256"):
        return _invalid("source_sha_changed_after_authorization")

    source_media = probe_media(source_path)
    output_media = probe_media(output_path)
    if source_record.get("media") != source_media:
        return _invalid("render_result_source_media_snapshot_changed")
    if output_record.get("media") != output_media:
        return _invalid("render_result_output_media_snapshot_changed")
    if source_record.get("audio") != request.get("source_audio"):
        return _invalid("render_result_source_audio_snapshot_changed")

    blockers: list[dict[str, Any]] = []
    if source_media.get("video_streams") != 1 or source_media.get("audio_streams") != 1:
        blockers.append({"code": "source_stream_layout_changed", "class": "technical_quality"})
    if output_media.get("video_streams") != 1 or output_media.get("audio_streams") != 1:
        blockers.append({"code": "output_stream_layout_invalid", "class": "technical_quality"})

    try:
        output_audio = _probe_audio_stream_contract(output_path)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        output_audio = {"error": str(exc)}
        blockers.append({"code": "output_audio_contract_unreadable", "class": "technical_quality"})
    else:
        if output_audio.get("codec_name") != DENOISE_RENDER_AUDIO_CODEC:
            blockers.append(
                {
                    "code": "output_audio_codec_changed",
                    "class": "technical_quality",
                    "observed": output_audio.get("codec_name"),
                    "required": DENOISE_RENDER_AUDIO_CODEC,
                }
            )
        if output_audio.get("channels") != DENOISE_VERIFICATION_CHANNELS:
            blockers.append(
                {
                    "code": "output_audio_channels_changed",
                    "class": "technical_quality",
                    "observed": output_audio.get("channels"),
                    "required": DENOISE_VERIFICATION_CHANNELS,
                }
            )
        if output_audio.get("sample_rate_hz") != DENOISE_VERIFICATION_SAMPLE_RATE_HZ:
            blockers.append(
                {
                    "code": "output_audio_sample_rate_changed",
                    "class": "technical_quality",
                    "observed": output_audio.get("sample_rate_hz"),
                    "required": DENOISE_VERIFICATION_SAMPLE_RATE_HZ,
                }
            )

    try:
        source_video_hash = decoded_video_sha256(source_path)
        output_video_hash = decoded_video_sha256(output_path)
    except (OSError, ValueError, RuntimeError) as exc:
        source_video_hash = None
        output_video_hash = None
        blockers.append(
            {
                "code": "decoded_video_verification_failed",
                "class": "technical_quality",
                "reason": str(exc),
            }
        )
    else:
        if source_video_hash != output_video_hash:
            blockers.append(
                {
                    "code": "decoded_video_changed_during_denoise",
                    "class": "technical_quality",
                    "source_video_sha256": source_video_hash,
                    "output_video_sha256": output_video_hash,
                }
            )

    try:
        source_audio_frames = decoded_audio_frame_count_48k_mono(source_path)
        output_audio_frames = decoded_audio_frame_count_48k_mono(output_path)
    except (OSError, ValueError, RuntimeError) as exc:
        source_audio_frames = None
        output_audio_frames = None
        blockers.append(
            {
                "code": "decoded_audio_timeline_verification_failed",
                "class": "technical_quality",
                "reason": str(exc),
            }
        )
    else:
        reported_timeline = render_result["timeline"]
        if source_audio_frames != reported_timeline["input_frames"]:
            blockers.append(
                {
                    "code": "independent_source_audio_frames_mismatch",
                    "class": "technical_quality",
                    "observed_frames": source_audio_frames,
                    "reported_input_frames": reported_timeline["input_frames"],
                }
            )
        if output_audio_frames != reported_timeline["final_frames"]:
            blockers.append(
                {
                    "code": "independent_output_audio_frames_mismatch",
                    "class": "technical_quality",
                    "observed_frames": output_audio_frames,
                    "reported_final_frames": reported_timeline["final_frames"],
                }
            )
        if source_audio_frames != output_audio_frames:
            blockers.append(
                {
                    "code": "independent_decoded_audio_timeline_changed",
                    "class": "technical_quality",
                    "source_frames": source_audio_frames,
                    "output_frames": output_audio_frames,
                }
            )

    technical_pass = not blockers
    return {
        "schema_version": DENOISE_POST_RENDER_SCHEMA_VERSION,
        "record_type": DENOISE_POST_RENDER_RECORD_TYPE,
        "status": "technical_denoise_pass" if technical_pass else "technical_denoise_fail",
        "valid_evidence": True,
        "technical_pass": technical_pass,
        "human_perceptual_review_required": True,
        "human_pass": False,
        "bindings": expected_bindings | {"render_result_sha256": render_digest},
        "source": {
            "sha256": actual_source_sha,
            "media": source_media,
            "decoded_video_sha256": source_video_hash,
            "decoded_audio_frames_48k_mono": source_audio_frames,
        },
        "output": {
            "sha256": actual_output_sha,
            "media": output_media,
            "audio_stream": output_audio,
            "decoded_video_sha256": output_video_hash,
            "decoded_audio_frames_48k_mono": output_audio_frames,
        },
        "reported_timeline": render_result["timeline"],
        "technical_policy": {
            "decoded_video_must_match": True,
            "output_audio_codec": DENOISE_RENDER_AUDIO_CODEC,
            "output_audio_channels": DENOISE_VERIFICATION_CHANNELS,
            "output_audio_sample_rate_hz": DENOISE_VERIFICATION_SAMPLE_RATE_HZ,
            "decoded_audio_frame_count_must_match_source": True,
            "raw_duration_delta_max_seconds": DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
            "alignment_search_allowed": False,
            "time_shift_allowed": False,
            "level_matching_allowed": False,
            "objective_or_perceptual_thresholds_added": False,
        },
        "blockers": blockers,
        "product_default": "preserve",
        "auto_apply": False,
    }


def save_denoise_post_render_verification(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
