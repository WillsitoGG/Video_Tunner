from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .approval import sha256_path
from .media import probe_media
from .normalization_execution_authorization import (
    validate_normalization_execution_authorization,
)
from .tools import resolve_tool

NORMALIZATION_RENDER_SCHEMA_VERSION = 1
NORMALIZATION_RENDER_RECORD_TYPE = "normalization_render_result"

_LOUDNORM_JSON = re.compile(
    r"\{\s*\"input_i\"\s*:.*?\"target_offset\"\s*:\s*\"[^\"]+\"\s*\}",
    re.DOTALL,
)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result and result not in (float("inf"), float("-inf")) else None


def parse_loudnorm_render_summary(stderr: str) -> dict[str, Any]:
    """Parse the final loudnorm JSON and require finite post-filter measurements."""
    matches = list(_LOUDNORM_JSON.finditer(stderr))
    if not matches:
        raise ValueError("FFmpeg loudnorm no devolvió summary JSON de render.")
    payload = json.loads(matches[-1].group(0))
    required = (
        "input_i",
        "input_tp",
        "input_lra",
        "input_thresh",
        "output_i",
        "output_tp",
        "output_lra",
        "output_thresh",
        "normalization_type",
        "target_offset",
    )
    if any(key not in payload for key in required):
        raise ValueError("FFmpeg loudnorm devolvió summary de render incompleto.")
    numeric = {
        "input_i": _finite(payload["input_i"]),
        "input_tp": _finite(payload["input_tp"]),
        "input_lra": _finite(payload["input_lra"]),
        "input_thresh": _finite(payload["input_thresh"]),
        "output_i": _finite(payload["output_i"]),
        "output_tp": _finite(payload["output_tp"]),
        "output_lra": _finite(payload["output_lra"]),
        "output_thresh": _finite(payload["output_thresh"]),
        "target_offset": _finite(payload["target_offset"]),
    }
    if any(value is None for value in numeric.values()):
        raise ValueError("FFmpeg loudnorm devolvió mediciones no finitas en render.")
    return {key: float(value) for key, value in numeric.items()} | {
        "normalization_type": str(payload["normalization_type"]).strip().lower(),
    }


def build_linear_loudnorm_filter(plan: dict[str, Any]) -> str:
    """Build only the already-approved linear loudnorm filter; never dynamic fallback."""
    if not isinstance(plan, dict):
        raise ValueError("Normalization plan debe ser objeto JSON.")
    policy = plan.get("policy")
    measurements = plan.get("measurements")
    targets = plan.get("targets")
    if not all(isinstance(value, dict) for value in (policy, measurements, targets)):
        raise ValueError("Normalization plan sin policy/measurements/targets.")
    if policy.get("mode") != "linear_only_fail_closed":
        raise ValueError("Sólo se admite linear_only_fail_closed.")
    if policy.get("dynamic_fallback_allowed"):
        raise ValueError("Dynamic loudnorm fallback está prohibido.")

    values = {
        "target_i": _finite(targets.get("target_i")),
        "target_tp": _finite(targets.get("target_tp")),
        "target_lra": _finite(targets.get("target_lra")),
        "measured_i": _finite(measurements.get("measured_i")),
        "measured_tp": _finite(measurements.get("measured_tp")),
        "measured_lra": _finite(measurements.get("measured_lra")),
        "measured_thresh": _finite(measurements.get("measured_thresh")),
    }
    if any(value is None for value in values.values()):
        raise ValueError("Normalization plan no contiene parámetros finitos completos.")
    v = {key: float(value) for key, value in values.items()}
    return (
        "loudnorm="
        f"I={v['target_i']:.6f}:"
        f"TP={v['target_tp']:.6f}:"
        f"LRA={v['target_lra']:.6f}:"
        f"measured_I={v['measured_i']:.6f}:"
        f"measured_TP={v['measured_tp']:.6f}:"
        f"measured_LRA={v['measured_lra']:.6f}:"
        f"measured_thresh={v['measured_thresh']:.6f}:"
        "linear=true:print_format=json"
    )


def validate_normalization_render_request(
    source: str | Path,
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
    plan_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    """Revalidate the complete Phase 3 normalization chain immediately before FFmpeg."""
    base = {"valid": False, "render_authorized": False, "auto_apply": False}
    authorization_digest = str(authorization_sha256 or "").strip().lower()
    if not _valid_sha256(authorization_digest):
        return base | {"status": "blocked_invalid_authorization_sha", "reason": "authorization_sha256_invalid"}

    validation = validate_normalization_execution_authorization(
        quality_audit,
        profile_decision,
        approval,
        plan,
        authorization,
        quality_audit_sha256=quality_audit_sha256,
        profile_decision_sha256=profile_decision_sha256,
        approval_sha256=approval_sha256,
        plan_sha256=plan_sha256,
    )
    if validation.get("status") != "valid_authorized":
        return base | {
            "status": "blocked_execution_authorization",
            "reason": validation.get("reason"),
            "authorization_status": validation.get("status"),
        }
    if not validation.get("normalization_render_authorization"):
        return base | {
            "status": "blocked_execution_authorization",
            "reason": "normalization_render_authorization_not_present",
        }

    source_path = Path(source).resolve()
    if not source_path.is_file():
        return base | {"status": "blocked_source_mismatch", "reason": "source_not_found"}
    actual_source_sha = sha256_path(source_path)
    bindings = plan.get("bindings")
    if not isinstance(bindings, dict):
        return base | {"status": "blocked_invalid_plan", "reason": "plan_bindings_missing"}
    expected_source_sha = str(bindings.get("quality_output_sha256") or "").lower()
    if actual_source_sha != expected_source_sha:
        return base | {
            "status": "blocked_source_mismatch",
            "reason": "quality_output_sha256_changed",
            "actual_source_sha256": actual_source_sha,
            "expected_source_sha256": expected_source_sha,
        }
    if validation.get("quality_output_sha256") != actual_source_sha:
        return base | {
            "status": "blocked_source_mismatch",
            "reason": "authorization_quality_output_sha256_mismatch",
        }

    media = probe_media(source_path)
    if media.get("video_streams") != 1 or media.get("audio_streams") != 1:
        return base | {
            "status": "blocked_media_layout",
            "reason": "normalization_renderer_requires_exactly_one_video_and_one_audio_stream",
            "video_streams": media.get("video_streams"),
            "audio_streams": media.get("audio_streams"),
        }

    try:
        filter_spec = build_linear_loudnorm_filter(plan)
    except ValueError as exc:
        return base | {"status": "blocked_invalid_plan", "reason": str(exc)}

    return base | {
        "status": "valid_normalization_render_request",
        "reason": None,
        "valid": True,
        "render_authorized": True,
        "source_sha256": actual_source_sha,
        "source_media": media,
        "authorization_sha256": authorization_digest,
        "profile_name": validation.get("profile_name"),
        "filter_spec": filter_spec,
    }


def render_normalized_media(
    source: str | Path,
    quality_audit: dict[str, Any],
    profile_decision: dict[str, Any],
    approval: dict[str, Any],
    plan: dict[str, Any],
    authorization: dict[str, Any],
    destination: str | Path,
    *,
    quality_audit_sha256: str,
    profile_decision_sha256: str,
    approval_sha256: str,
    plan_sha256: str,
    authorization_sha256: str,
) -> dict[str, Any]:
    """Render one explicitly authorized linear normalization and record provenance.

    The source video stream is stream-copied. Only the first/sole audio stream is
    re-encoded after loudnorm. If FFmpeg reports dynamic normalization despite the
    preflight constraints, the produced file is deleted and the render fails closed.
    """
    source_path = Path(source).resolve()
    destination_path = Path(destination).resolve()
    if source_path == destination_path:
        raise ValueError("El original/render 2E nunca puede sobrescribirse.")

    validation = validate_normalization_render_request(
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
    if validation.get("status") != "valid_normalization_render_request":
        raise ValueError(
            "Normalization render gate bloqueado: "
            f"{validation.get('status')} ({validation.get('reason')})"
        )

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-y",
            "-i",
            str(source_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-map_metadata",
            "0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-af",
            validation["filter_spec"],
            str(destination_path),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        destination_path.unlink(missing_ok=True)
        raise RuntimeError(f"FFmpeg no pudo renderizar normalización:\n{completed.stderr}")

    try:
        loudnorm_summary = parse_loudnorm_render_summary(completed.stderr)
    except Exception:
        destination_path.unlink(missing_ok=True)
        raise
    if loudnorm_summary.get("normalization_type") != "linear":
        destination_path.unlink(missing_ok=True)
        raise RuntimeError(
            "FFmpeg cayó fuera de LINEAR_MODE; output eliminado para impedir fallback dinámico."
        )
    if not destination_path.is_file():
        raise RuntimeError("FFmpeg terminó sin crear el output normalizado.")

    source_sha_after = sha256_path(source_path)
    if source_sha_after != validation["source_sha256"]:
        destination_path.unlink(missing_ok=True)
        raise RuntimeError("El source cambió durante el render; output invalidado.")

    output_media = probe_media(destination_path)
    return {
        "schema_version": NORMALIZATION_RENDER_SCHEMA_VERSION,
        "record_type": NORMALIZATION_RENDER_RECORD_TYPE,
        "status": "normalization_render_complete",
        "source": {
            "file": source_path.name,
            "sha256": source_sha_after,
            "media": validation["source_media"],
        },
        "output": {
            "file": destination_path.name,
            "sha256": sha256_path(destination_path),
            "media": output_media,
        },
        "bindings": {
            "quality_audit_sha256": str(quality_audit_sha256).strip().lower(),
            "profile_decision_sha256": str(profile_decision_sha256).strip().lower(),
            "approval_sha256": str(approval_sha256).strip().lower(),
            "plan_sha256": str(plan_sha256).strip().lower(),
            "authorization_sha256": str(authorization_sha256).strip().lower(),
            "profile_name": validation.get("profile_name"),
        },
        "ffmpeg_loudnorm": loudnorm_summary,
        "video_policy": "stream_copy_first_and_only_video_stream",
        "audio_policy": "aac_192k_first_and_only_audio_stream_after_authorized_linear_loudnorm",
        "technical_post_render_verification_required": True,
        "human_perceptual_review_required": True,
        "technical_pass": False,
        "human_pass": False,
        "auto_apply": False,
    }


def save_normalization_render_result(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
