from __future__ import annotations

import math
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .tools import resolve_tool

SAMPLE_RATE = 16000
EDGE_WINDOW_SECONDS = 0.080
EDGE_MICRO_WINDOW_SECONDS = 0.012
SILENCE_DBFS = -42.0
MAX_RMS_DELTA_DB = 12.0
MAX_BOUNDARY_SAMPLE_JUMP = 0.35
MAX_BOUNDARY_JUMP_RATIO = 1.25


def _require_numpy():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover - guarded by analysis extras/runtime doctor
        raise RuntimeError(
            "La validación acústica de joins requiere NumPy dentro del runtime de análisis."
        ) from exc
    return np


def _decode_master_pcm16(
    master_audio: str | Path,
    destination: str | Path,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> Path:
    """Decode the accredited master once to raw mono PCM16 for random window access."""
    source = Path(master_audio)
    if not source.is_file():
        raise FileNotFoundError(f"No existe el master audio: {source}")
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
        raise RuntimeError(f"FFmpeg no pudo decodificar el master para join acoustics:\n{completed.stderr}")
    if not target.is_file() or target.stat().st_size < 2:
        raise RuntimeError("FFmpeg terminó sin generar PCM válido para join acoustics.")
    return target


def _rms(samples: Any) -> float:
    np = _require_numpy()
    if len(samples) == 0:
        return 0.0
    values = np.asarray(samples, dtype=np.float32)
    return float(np.sqrt(np.mean(values * values)))


def _dbfs(value: float) -> float:
    if value <= 1e-8:
        return -120.0
    return float(20.0 * math.log10(value))


def measure_join_edges(
    left_samples: Any,
    right_samples: Any,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> dict[str, Any]:
    """Measure two PCM float windows that would become adjacent after a hypothetical cut."""
    np = _require_numpy()
    left = np.asarray(left_samples, dtype=np.float32)
    right = np.asarray(right_samples, dtype=np.float32)
    micro_count = max(1, int(round(EDGE_MICRO_WINDOW_SECONDS * sample_rate)))

    if left.size == 0 or right.size == 0:
        return {
            "measurement_available": False,
            "reason": "empty_edge_window",
        }

    left_rms = _rms(left)
    right_rms = _rms(right)
    left_edge_rms = _rms(left[-micro_count:])
    right_edge_rms = _rms(right[:micro_count])
    left_peak = float(np.max(np.abs(left)))
    right_peak = float(np.max(np.abs(right)))
    boundary_jump = float(abs(float(left[-1]) - float(right[0])))
    reference_peak = max(left_peak, right_peak, 1e-6)
    jump_ratio = boundary_jump / reference_peak

    return {
        "measurement_available": True,
        "sample_rate": sample_rate,
        "left_samples": int(left.size),
        "right_samples": int(right.size),
        "left_rms_dbfs": round(_dbfs(left_rms), 4),
        "right_rms_dbfs": round(_dbfs(right_rms), 4),
        "rms_delta_db": round(abs(_dbfs(left_rms) - _dbfs(right_rms)), 4),
        "left_edge_rms_dbfs": round(_dbfs(left_edge_rms), 4),
        "right_edge_rms_dbfs": round(_dbfs(right_edge_rms), 4),
        "left_peak": round(left_peak, 6),
        "right_peak": round(right_peak, 6),
        "boundary_sample_jump": round(boundary_jump, 6),
        "boundary_jump_ratio": round(jump_ratio, 6),
    }


def classify_join_acoustics(metrics: dict[str, Any]) -> tuple[str, list[str]]:
    """Classify measured edge evidence without ever authorizing a cut."""
    if not metrics.get("measurement_available"):
        return "insufficient_audio_context", [
            "No hay ventanas acústicas bilaterales suficientes para medir el empalme."
        ]

    left_db = float(metrics["left_rms_dbfs"])
    right_db = float(metrics["right_rms_dbfs"])
    left_edge_db = float(metrics["left_edge_rms_dbfs"])
    right_edge_db = float(metrics["right_edge_rms_dbfs"])
    rms_delta = float(metrics["rms_delta_db"])
    jump = float(metrics["boundary_sample_jump"])
    jump_ratio = float(metrics["boundary_jump_ratio"])

    both_low_energy = (
        left_db <= SILENCE_DBFS
        and right_db <= SILENCE_DBFS
        and left_edge_db <= SILENCE_DBFS
        and right_edge_db <= SILENCE_DBFS
    )
    if both_low_energy:
        return "low_energy_boundary_context", [
            "Ambos bordes están en energía muy baja; es evidencia acústica favorable, no permiso de corte."
        ]

    level_risk = rms_delta > MAX_RMS_DELTA_DB
    waveform_risk = (
        jump > MAX_BOUNDARY_SAMPLE_JUMP
        and jump_ratio > MAX_BOUNDARY_JUMP_RATIO
        and max(left_edge_db, right_edge_db) > SILENCE_DBFS
    )

    if level_risk and waveform_risk:
        return "combined_discontinuity_risk", [
            "El join hipotético presenta salto de nivel y discontinuidad instantánea de waveform."
        ]
    if level_risk:
        return "level_discontinuity_risk", [
            "La diferencia RMS entre ambos lados supera el umbral conservador."
        ]
    if waveform_risk:
        return "waveform_discontinuity_risk", [
            "El salto de muestra en el punto de unión supera el umbral conservador."
        ]
    return "acoustic_context_only", [
        "No se activa una guarda acústica v1; la medición sigue sin autorizar un corte."
    ]


def _base_assessment(join: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": "",
        "join_assessment_id": join.get("id"),
        "candidate_id": join.get("candidate_id"),
        "candidate_kind": join.get("candidate_kind"),
        "target_span": join.get("target_span"),
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def assess_join_edge_samples(
    join: dict[str, Any],
    left_samples: Any,
    right_samples: Any,
    *,
    sample_rate: int = SAMPLE_RATE,
) -> dict[str, Any]:
    """Build the production acoustic assessment from already materialised edge samples."""
    metrics = measure_join_edges(left_samples, right_samples, sample_rate=sample_rate)
    status, rationale = classify_join_acoustics(metrics)
    return {
        **_base_assessment(join),
        "status": status,
        "metrics": metrics,
        "rationale": rationale,
        "measurement_available": bool(metrics.get("measurement_available")),
    }


def _blocked_record(join: dict[str, Any], *, reason: str) -> dict[str, Any]:
    return {
        **_base_assessment(join),
        "status": "blocked_by_context",
        "metrics": None,
        "rationale": [reason],
        "measurement_available": False,
    }


def _insufficient_record(
    join: dict[str, Any],
    *,
    target_span: dict[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    return {
        **_base_assessment(join),
        "status": "insufficient_audio_context",
        "target_span": target_span,
        "metrics": {"measurement_available": False, "reason": reason},
        "rationale": ["No existe contexto acústico bilateral suficiente; fail-safe."],
        "measurement_available": False,
    }


def build_acoustic_join_assessments(
    master_audio: str | Path,
    join_assessments: list[dict[str, Any]],
    *,
    sample_rate: int = SAMPLE_RATE,
) -> list[dict[str, Any]]:
    """Measure real master-audio edges for context-clean join assessments.

    The master is decoded once to raw PCM16 in a temporary directory and exposed
    through NumPy memmap. Only `join_context_only` records are measured. Any
    lexical/timeline risk remains blocked before acoustic analysis.
    """
    np = _require_numpy()
    eligible = [item for item in join_assessments if item.get("status") == "join_context_only"]
    results: list[dict[str, Any]] = []

    if not eligible:
        for join in join_assessments:
            results.append(
                _blocked_record(
                    join,
                    reason="El join ya está bloqueado por evidencia timeline/léxica/segmental previa.",
                )
            )
        for index, item in enumerate(results, start=1):
            item["id"] = f"acoustic-join-assessment-{index:04d}"
        return results

    with tempfile.TemporaryDirectory(prefix="video_tunner_join_audio_") as temp:
        pcm_path = _decode_master_pcm16(
            master_audio,
            Path(temp) / "master_mono16k.pcm",
            sample_rate=sample_rate,
        )
        pcm = np.memmap(pcm_path, dtype="<i2", mode="r")
        total_samples = int(pcm.shape[0])
        duration = total_samples / float(sample_rate)
        edge_count = int(round(EDGE_WINDOW_SECONDS * sample_rate))

        for join in join_assessments:
            if join.get("status") != "join_context_only":
                results.append(
                    _blocked_record(
                        join,
                        reason="El join ya está bloqueado por evidencia timeline/léxica/segmental previa.",
                    )
                )
                continue

            target = join.get("target_span") or {}
            try:
                cut_start = float(target["start"])
                cut_end = float(target["end"])
            except (KeyError, TypeError, ValueError):
                results.append(
                    _insufficient_record(join, target_span=None, reason="missing_target_timestamps")
                )
                continue

            if cut_start < EDGE_WINDOW_SECONDS or cut_end <= cut_start or cut_end + EDGE_WINDOW_SECONDS > duration:
                results.append(
                    _insufficient_record(
                        join,
                        target_span=target,
                        reason="target_too_close_to_audio_edge_or_invalid",
                    )
                )
                continue

            left_end = int(round(cut_start * sample_rate))
            right_start = int(round(cut_end * sample_rate))
            left_start = left_end - edge_count
            right_end = right_start + edge_count
            if left_start < 0 or right_end > total_samples or left_end <= left_start or right_end <= right_start:
                results.append(
                    _insufficient_record(join, target_span=target, reason="window_index_out_of_bounds")
                )
                continue

            left = np.asarray(pcm[left_start:left_end], dtype=np.float32) / 32768.0
            right = np.asarray(pcm[right_start:right_end], dtype=np.float32) / 32768.0
            results.append(assess_join_edge_samples(join, left, right, sample_rate=sample_rate))

        del pcm

    for index, item in enumerate(results, start=1):
        item["id"] = f"acoustic-join-assessment-{index:04d}"
    return results
