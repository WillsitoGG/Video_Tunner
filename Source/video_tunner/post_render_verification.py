from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .acoustic_join import (
    EDGE_WINDOW_SECONDS,
    SAMPLE_RATE,
    classify_join_acoustics,
    measure_join_edges,
)
from .approval import sha256_path
from .media import probe_media
from .semantic_render import validate_semantic_render_request
from .tools import resolve_tool

POST_RENDER_VERIFICATION_SCHEMA_VERSION = 1
POST_RENDER_VERIFICATION_RECORD_TYPE = "semantic_render_verification"
MAX_OUTPUT_DURATION_ERROR_SECONDS = 0.20
EXPECTED_OUTPUT_VIDEO_STREAMS = 1
EXPECTED_OUTPUT_AUDIO_STREAMS = 1
PASSING_POST_RENDER_JOIN_STATUSES = frozenset(
    {"acoustic_context_only", "low_energy_boundary_context"}
)


def _require_numpy():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - guarded by runtime/CI
        raise RuntimeError("Post-render join verification requiere NumPy.") from exc
    return np


def _decode_output_pcm16(
    output: str | Path,
    destination: str | Path,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> Path:
    source = Path(output)
    if not source.is_file():
        raise FileNotFoundError(f"No existe el output renderizado: {source}")
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-c:a",
            "pcm_s16le",
            "-f",
            "s16le",
            str(target),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo decodificar el output para post-render audit:\n{completed.stderr}")
    if not target.is_file() or target.stat().st_size < 2:
        raise RuntimeError("FFmpeg no generó PCM válido para post-render audit.")
    return target


def rendered_join_points(edits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map source cut spans to their resulting join positions on the output timeline."""
    ordered = sorted(edits, key=lambda item: (float(item["start"]), float(item["end"])))
    removed_before = 0.0
    result: list[dict[str, Any]] = []
    previous_end: float | None = None
    for index, edit in enumerate(ordered, start=1):
        start = float(edit["start"])
        end = float(edit["end"])
        if start < 0.0 or end <= start:
            raise ValueError(f"Edit #{index} contiene un span inválido.")
        if previous_end is not None and start < previous_end - 1e-9:
            raise ValueError("Semantic Edit Plan contiene edits solapados.")
        output_join = start - removed_before
        result.append(
            {
                "edit_id": edit.get("id"),
                "candidate_id": edit.get("candidate_id"),
                "source_start": round(start, 6),
                "source_end": round(end, 6),
                "removed_seconds": round(end - start, 6),
                "output_join_seconds": round(output_join, 6),
            }
        )
        removed_before += end - start
        previous_end = end
    return result


def _measure_output_joins(
    output: str | Path,
    plan: dict[str, Any],
    *,
    sample_rate: int = SAMPLE_RATE,
) -> list[dict[str, Any]]:
    np = _require_numpy()
    join_points = rendered_join_points(list(plan.get("edits") or []))
    if not join_points:
        return []

    with tempfile.TemporaryDirectory(prefix="video_tunner_post_render_") as temp:
        pcm_path = _decode_output_pcm16(
            output,
            Path(temp) / "output_mono16k.pcm",
            sample_rate=sample_rate,
        )
        pcm = np.memmap(pcm_path, dtype="<i2", mode="r")
        total_samples = int(pcm.shape[0])
        duration = total_samples / float(sample_rate)
        edge_count = int(round(EDGE_WINDOW_SECONDS * sample_rate))
        results: list[dict[str, Any]] = []

        for index, point in enumerate(join_points, start=1):
            join_time = float(point["output_join_seconds"])
            center = int(round(join_time * sample_rate))
            left_start = center - edge_count
            right_end = center + edge_count
            if (
                join_time < EDGE_WINDOW_SECONDS
                or join_time + EDGE_WINDOW_SECONDS > duration
                or left_start < 0
                or right_end > total_samples
            ):
                results.append(
                    {
                        "id": f"post-render-join-{index:04d}",
                        **point,
                        "status": "insufficient_audio_context",
                        "metrics": {
                            "measurement_available": False,
                            "reason": "join_too_close_to_output_edge",
                        },
                        "technical_pass": False,
                    }
                )
                continue

            left = np.asarray(pcm[left_start:center], dtype=np.float32) / 32768.0
            right = np.asarray(pcm[center:right_end], dtype=np.float32) / 32768.0
            metrics = measure_join_edges(left, right, sample_rate=sample_rate)
            status, rationale = classify_join_acoustics(metrics)
            results.append(
                {
                    "id": f"post-render-join-{index:04d}",
                    **point,
                    "status": status,
                    "metrics": metrics,
                    "rationale": rationale,
                    "technical_pass": status in PASSING_POST_RENDER_JOIN_STATUSES,
                }
            )

        del pcm
    return results


def build_post_render_verification(
    source: str | Path,
    output: str | Path,
    analysis: dict[str, Any],
    proposal: dict[str, Any],
    authorization: dict[str, Any],
    plan: dict[str, Any],
    *,
    analysis_sha256: str,
    proposal_sha256: str,
    authorization_sha256: str,
    output_sha256: str | None = None,
) -> dict[str, Any]:
    """Build a fail-safe technical verification report after semantic rendering.

    Passing this report proves structural/provenance/acoustic v1 checks only. It
    deliberately cannot close Phase 2E without separate human perceptual evidence.
    """
    source_path = Path(source).resolve()
    output_path = Path(output).resolve()
    blockers: list[dict[str, Any]] = []

    if source_path == output_path:
        blockers.append({"code": "source_output_same_path"})

    chain = validate_semantic_render_request(
        source_path,
        analysis,
        proposal,
        authorization,
        plan,
        analysis_sha256=analysis_sha256,
        proposal_sha256=proposal_sha256,
        authorization_sha256=authorization_sha256,
    )
    if chain.get("status") != "valid_semantic_render_request":
        blockers.append(
            {
                "code": "invalid_execution_chain",
                "status": chain.get("status"),
                "reason": chain.get("reason"),
            }
        )

    if not source_path.is_file():
        raise FileNotFoundError(f"No existe el source original: {source_path}")
    if not output_path.is_file():
        raise FileNotFoundError(f"No existe el output renderizado: {output_path}")

    source_sha = sha256_path(source_path)
    output_sha = (output_sha256 or sha256_path(output_path)).strip().lower()
    if output_sha == source_sha:
        blockers.append({"code": "output_identical_to_source"})

    source_probe = probe_media(source_path)
    output_probe = probe_media(output_path)
    expected_duration = float((plan.get("summary") or {}).get("estimated_output_seconds", -1.0))
    actual_duration = float(output_probe["duration_seconds"])
    duration_error = abs(actual_duration - expected_duration)
    duration_pass = expected_duration > 0.0 and duration_error <= MAX_OUTPUT_DURATION_ERROR_SECONDS
    if not duration_pass:
        blockers.append(
            {
                "code": "output_duration_mismatch",
                "expected_seconds": round(expected_duration, 6),
                "actual_seconds": round(actual_duration, 6),
                "absolute_error_seconds": round(duration_error, 6),
                "max_error_seconds": MAX_OUTPUT_DURATION_ERROR_SECONDS,
            }
        )

    stream_pass = (
        int(output_probe["video_streams"]) == EXPECTED_OUTPUT_VIDEO_STREAMS
        and int(output_probe["audio_streams"]) == EXPECTED_OUTPUT_AUDIO_STREAMS
    )
    if not stream_pass:
        blockers.append(
            {
                "code": "output_stream_contract_mismatch",
                "expected_video_streams": EXPECTED_OUTPUT_VIDEO_STREAMS,
                "actual_video_streams": int(output_probe["video_streams"]),
                "expected_audio_streams": EXPECTED_OUTPUT_AUDIO_STREAMS,
                "actual_audio_streams": int(output_probe["audio_streams"]),
            }
        )

    join_audits = _measure_output_joins(output_path, plan)
    failed_joins = [item for item in join_audits if not item.get("technical_pass")]
    if failed_joins:
        blockers.append(
            {
                "code": "post_render_join_gate_failed",
                "failed_join_ids": [item["id"] for item in failed_joins],
                "statuses": [item["status"] for item in failed_joins],
            }
        )

    technical_pass = not blockers
    return {
        "schema_version": POST_RENDER_VERIFICATION_SCHEMA_VERSION,
        "record_type": POST_RENDER_VERIFICATION_RECORD_TYPE,
        "status": "technical_post_render_pass" if technical_pass else "technical_post_render_failed",
        "technical_pass": technical_pass,
        "blockers": blockers,
        "execution_chain": {
            "status": chain.get("status"),
            "valid": bool(chain.get("valid")),
            "analysis_sha256": analysis_sha256.strip().lower(),
            "proposal_sha256": proposal_sha256.strip().lower(),
            "authorization_sha256": authorization_sha256.strip().lower(),
            "plan_fingerprint": plan.get("plan_fingerprint"),
        },
        "source": {
            "file": source_path.name,
            "sha256": source_sha,
            "duration_seconds": float(source_probe["duration_seconds"]),
            "video_streams": int(source_probe["video_streams"]),
            "audio_streams": int(source_probe["audio_streams"]),
        },
        "output": {
            "file": output_path.name,
            "sha256": output_sha,
            "duration_seconds": actual_duration,
            "video_streams": int(output_probe["video_streams"]),
            "audio_streams": int(output_probe["audio_streams"]),
        },
        "duration_verification": {
            "expected_seconds": round(expected_duration, 6),
            "actual_seconds": round(actual_duration, 6),
            "absolute_error_seconds": round(duration_error, 6),
            "max_error_seconds": MAX_OUTPUT_DURATION_ERROR_SECONDS,
            "pass": duration_pass,
        },
        "stream_verification": {
            "expected_video_streams": EXPECTED_OUTPUT_VIDEO_STREAMS,
            "expected_audio_streams": EXPECTED_OUTPUT_AUDIO_STREAMS,
            "pass": stream_pass,
        },
        "post_render_join_audits": join_audits,
        "summary": {
            "edit_count": len(list(plan.get("edits") or [])),
            "join_audit_count": len(join_audits),
            "join_technical_pass_count": sum(bool(item.get("technical_pass")) for item in join_audits),
            "join_technical_fail_count": len(failed_joins),
        },
        "human_perceptual_verification": {
            "required": True,
            "completed": False,
            "pass": False,
        },
        "phase2e_closeout_ready": False,
        "auto_apply": False,
    }


def save_post_render_verification(report: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
