from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

from .approval import sha256_path
from .audiovisual_quality import measure_audio_loudness
from .media import probe_media
from .normalization_render import (
    NORMALIZATION_RENDER_RECORD_TYPE,
    NORMALIZATION_RENDER_SCHEMA_VERSION,
    validate_normalization_render_request,
)
from .tools import resolve_tool

NORMALIZATION_POST_RENDER_SCHEMA_VERSION = 1
NORMALIZATION_POST_RENDER_RECORD_TYPE = "normalization_post_render_verification"
PROGRAMME_LOUDNESS_TOLERANCE_LU = 0.5
DURATION_TOLERANCE_SECONDS = 0.15

_HASH_LINE = re.compile(r"SHA256=([0-9a-fA-F]{64})")


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result or result in (float("inf"), float("-inf")):
        return None
    return result


def decoded_video_sha256(source: str | Path) -> str:
    """Hash decoded video frames so a normalization-only render cannot alter picture content."""
    path = Path(source)
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
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo calcular hash de vídeo decodificado:\n{completed.stderr}")
    match = _HASH_LINE.search(completed.stdout)
    if not match:
        raise ValueError("FFmpeg hash muxer no devolvió SHA256 de vídeo.")
    return match.group(1).lower()


def _invalid(reason: str, **extra: Any) -> dict[str, Any]:
    return {
        "schema_version": NORMALIZATION_POST_RENDER_SCHEMA_VERSION,
        "record_type": NORMALIZATION_POST_RENDER_RECORD_TYPE,
        "status": "invalid_evidence",
        "valid_evidence": False,
        "technical_pass": False,
        "human_perceptual_review_required": True,
        "human_pass": False,
        "blockers": [{"code": reason, "class": "invalid_evidence"}],
        "auto_apply": False,
    } | extra


def build_normalization_post_render_verification(
    source: str | Path,
    output: str | Path,
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    render_result: dict[str, Any],
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
    plan_sha256: str,
    authorization_sha256: str,
    render_result_sha256: str,
) -> dict[str, Any]:
    """Independently verify an authorized normalization render.

    Invalid/stale provenance is kept distinct from an actual technical quality
    failure. Technical PASS never substitutes the later human perceptual review.
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

    request = validate_normalization_render_request(
        source_path,
        quality_audit,
        profile_decision,
        approval,
        plan,
        authorization,
        quality_audit_sha256=quality_audit_sha256,
        profile_decision_sha256=profile_decision_sha256,
        approval_sha256=approval_sha256,
        plan_sha256=plan_sha256,
        authorization_sha256=authorization_sha256,
    )
    if request.get("status") != "valid_normalization_render_request":
        return _invalid(
            "stale_or_invalid_normalization_chain",
            upstream_status=request.get("status"),
            upstream_reason=request.get("reason"),
        )

    if not isinstance(render_result, dict):
        return _invalid("render_result_not_object")
    if render_result.get("schema_version") != NORMALIZATION_RENDER_SCHEMA_VERSION:
        return _invalid("unsupported_render_result_schema")
    if render_result.get("record_type") != NORMALIZATION_RENDER_RECORD_TYPE:
        return _invalid("invalid_render_result_type")
    if render_result.get("status") != "normalization_render_complete":
        return _invalid("render_result_not_complete")
    if render_result.get("technical_pass") or render_result.get("human_pass") or render_result.get("auto_apply"):
        return _invalid("render_result_contains_premature_pass_or_auto_apply")
    if not render_result.get("technical_post_render_verification_required"):
        return _invalid("render_result_bypasses_technical_verification")
    if not render_result.get("human_perceptual_review_required"):
        return _invalid("render_result_bypasses_human_review")

    expected_bindings = {
        "quality_audit_sha256": str(quality_audit_sha256).strip().lower(),
        "profile_decision_sha256": str(profile_decision_sha256).strip().lower(),
        "approval_sha256": str(approval_sha256).strip().lower(),
        "plan_sha256": str(plan_sha256).strip().lower(),
        "authorization_sha256": str(authorization_sha256).strip().lower(),
        "profile_name": request.get("profile_name"),
    }
    if render_result.get("bindings") != expected_bindings:
        return _invalid("render_result_bindings_changed")

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

    loudnorm = render_result.get("ffmpeg_loudnorm")
    if not isinstance(loudnorm, dict) or str(loudnorm.get("normalization_type") or "").lower() != "linear":
        return _invalid("render_result_not_linear")

    targets = plan.get("targets")
    if not isinstance(targets, dict):
        return _invalid("plan_targets_missing")
    target_i = _finite(targets.get("target_i"))
    target_tp = _finite(targets.get("target_tp"))
    if target_i is None or target_tp is None:
        return _invalid("plan_targets_nonfinite")

    blockers: list[dict[str, Any]] = []
    if source_media.get("video_streams") != 1 or source_media.get("audio_streams") != 1:
        blockers.append({"code": "source_stream_layout_changed", "class": "technical_quality"})
    if output_media.get("video_streams") != 1 or output_media.get("audio_streams") != 1:
        blockers.append({"code": "output_stream_layout_invalid", "class": "technical_quality"})

    duration_delta = abs(float(output_media["duration_seconds"]) - float(source_media["duration_seconds"]))
    if duration_delta > DURATION_TOLERANCE_SECONDS + 1e-9:
        blockers.append(
            {
                "code": "duration_delta_exceeded",
                "class": "technical_quality",
                "delta_seconds": round(duration_delta, 6),
                "tolerance_seconds": DURATION_TOLERANCE_SECONDS,
            }
        )

    source_video_hash = decoded_video_sha256(source_path)
    output_video_hash = decoded_video_sha256(output_path)
    if source_video_hash != output_video_hash:
        blockers.append(
            {
                "code": "decoded_video_changed_during_audio_normalization",
                "class": "technical_quality",
                "source_video_sha256": source_video_hash,
                "output_video_sha256": output_video_hash,
            }
        )

    independent_audio = measure_audio_loudness(output_path)
    measured_i = _finite(independent_audio.get("integrated_lufs"))
    measured_tp = _finite(independent_audio.get("true_peak_dbtp"))
    if measured_i is None or measured_tp is None:
        blockers.append({"code": "independent_audio_measurement_nonfinite", "class": "technical_quality"})
    else:
        loudness_error = abs(measured_i - target_i)
        if loudness_error > PROGRAMME_LOUDNESS_TOLERANCE_LU + 1e-9:
            blockers.append(
                {
                    "code": "programme_loudness_out_of_tolerance",
                    "class": "technical_quality",
                    "measured_lufs": measured_i,
                    "target_lufs": target_i,
                    "absolute_error_lu": round(loudness_error, 4),
                    "tolerance_lu": PROGRAMME_LOUDNESS_TOLERANCE_LU,
                }
            )
        if measured_tp > target_tp + 1e-9:
            blockers.append(
                {
                    "code": "true_peak_limit_exceeded",
                    "class": "technical_quality",
                    "measured_dbtp": measured_tp,
                    "maximum_dbtp": target_tp,
                }
            )

    reported_i = _finite(loudnorm.get("output_i"))
    reported_tp = _finite(loudnorm.get("output_tp"))
    if reported_i is None or reported_tp is None:
        blockers.append({"code": "ffmpeg_render_summary_nonfinite", "class": "technical_quality"})
    else:
        if abs(reported_i - target_i) > PROGRAMME_LOUDNESS_TOLERANCE_LU + 1e-9:
            blockers.append(
                {
                    "code": "ffmpeg_reported_loudness_out_of_tolerance",
                    "class": "technical_quality",
                    "reported_lufs": reported_i,
                    "target_lufs": target_i,
                    "tolerance_lu": PROGRAMME_LOUDNESS_TOLERANCE_LU,
                }
            )
        if reported_tp > target_tp + 1e-9:
            blockers.append(
                {
                    "code": "ffmpeg_reported_true_peak_limit_exceeded",
                    "class": "technical_quality",
                    "reported_dbtp": reported_tp,
                    "maximum_dbtp": target_tp,
                }
            )

    technical_pass = not blockers
    return {
        "schema_version": NORMALIZATION_POST_RENDER_SCHEMA_VERSION,
        "record_type": NORMALIZATION_POST_RENDER_RECORD_TYPE,
        "status": "technical_normalization_pass" if technical_pass else "technical_normalization_fail",
        "valid_evidence": True,
        "technical_pass": technical_pass,
        "human_perceptual_review_required": True,
        "human_pass": False,
        "bindings": expected_bindings | {"render_result_sha256": render_digest},
        "source": {
            "sha256": actual_source_sha,
            "media": source_media,
            "decoded_video_sha256": source_video_hash,
        },
        "output": {
            "sha256": actual_output_sha,
            "media": output_media,
            "decoded_video_sha256": output_video_hash,
        },
        "targets": {
            "integrated_lufs": target_i,
            "max_true_peak_dbtp": target_tp,
            "programme_loudness_tolerance_lu": PROGRAMME_LOUDNESS_TOLERANCE_LU,
            "duration_tolerance_seconds": DURATION_TOLERANCE_SECONDS,
        },
        "independent_audio_measurement": independent_audio,
        "ffmpeg_render_summary": loudnorm,
        "duration_delta_seconds": round(duration_delta, 6),
        "blockers": blockers,
        "auto_apply": False,
    }
