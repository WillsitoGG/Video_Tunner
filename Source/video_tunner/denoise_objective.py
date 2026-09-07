from __future__ import annotations

import math
from typing import Any, Callable

import numpy as np


DENOISE_OBJECTIVE_SCHEMA_VERSION = 1
DENOISE_OBJECTIVE_RECORD_TYPE = "denoise_objective_measurement"
DENOISE_OBJECTIVE_POLICY_ID = "paired_clean_noisy_sisdr_stoi_v1"


def _mono_finite_vector(value: Any, *, label: str) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.ndim != 1:
        raise ValueError(f"{label} debe ser audio mono 1-D.")
    if array.size < 2:
        raise ValueError(f"{label} no contiene suficientes muestras.")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{label} contiene muestras no finitas.")
    return array


def right_tail_normalize(value: Any, *, target_frame_count: int, padding_value: float = 0.0) -> tuple[np.ndarray, dict[str, Any]]:
    """Normalize only the right edge to an exact frame count.

    This deliberately performs no alignment search, time shift, resampling or
    level matching. Short estimates are right-padded and long estimates are
    right-trimmed while preserving frame zero exactly.
    """
    samples = _mono_finite_vector(value, label="value")
    target = int(target_frame_count)
    if target < 2:
        raise ValueError("target_frame_count debe ser >= 2.")
    pad = float(padding_value)
    if not math.isfinite(pad):
        raise ValueError("padding_value debe ser finito.")

    original = int(samples.size)
    if original == target:
        normalized = samples.copy()
        action = "none"
    elif original < target:
        normalized = np.pad(samples, (0, target - original), mode="constant", constant_values=pad)
        action = "right_pad"
    else:
        normalized = samples[:target].copy()
        action = "right_trim"

    return normalized, {
        "method": "right_pad_or_right_trim_only",
        "original_frame_count": original,
        "target_frame_count": target,
        "raw_frame_delta": original - target,
        "action": action,
        "alignment_search_performed": False,
        "time_shift_performed": False,
        "level_matching_performed": False,
        "padding_value": pad,
    }


def scale_invariant_sdr(reference: Any, estimate: Any) -> float:
    """Compute SI-SDR as defined by Le Roux et al. (ICASSP 2019).

    Both signals are centered first. The estimate is projected onto the
    reference and the residual is treated as distortion. No alignment search,
    resampling or pre-metric level matching is performed here.
    """
    clean = _mono_finite_vector(reference, label="reference")
    degraded = _mono_finite_vector(estimate, label="estimate")
    if clean.shape != degraded.shape:
        raise ValueError("SI-SDR requiere reference y estimate con idéntico frame count.")

    clean = clean - float(np.mean(clean))
    degraded = degraded - float(np.mean(degraded))
    clean_energy = float(np.dot(clean, clean))
    if clean_energy <= np.finfo(np.float64).eps:
        raise ValueError("SI-SDR no está definido para una referencia sin energía.")

    scale = float(np.dot(degraded, clean)) / clean_energy
    projected = scale * clean
    residual = degraded - projected
    projected_energy = float(np.dot(projected, projected))
    residual_energy = float(np.dot(residual, residual))

    if projected_energy <= np.finfo(np.float64).eps:
        return float("-inf")
    if residual_energy <= np.finfo(np.float64).eps:
        return float("inf")
    return 10.0 * math.log10(projected_energy / residual_energy)


def normalized_rmse(reference: Any, estimate: Any) -> float:
    clean = _mono_finite_vector(reference, label="reference")
    test = _mono_finite_vector(estimate, label="estimate")
    if clean.shape != test.shape:
        raise ValueError("NRMSE requiere reference y estimate con idéntico frame count.")
    clean_energy = float(np.dot(clean, clean))
    if clean_energy <= np.finfo(np.float64).eps:
        raise ValueError("NRMSE no está definido para una referencia sin energía.")
    error = test - clean
    value = math.sqrt(float(np.dot(error, error)) / clean_energy)
    if not math.isfinite(value):
        raise ValueError("NRMSE devolvió un valor no finito.")
    return value


def _resolve_stoi() -> Callable[..., float]:
    try:
        from pystoi import stoi
    except ImportError as exc:  # evaluation dependency, deliberately not product runtime
        raise RuntimeError(
            "STOI requiere la dependencia de evaluación pystoi==0.4.1; "
            "no forma parte del runtime portable de producto."
        ) from exc
    return stoi


def _validated_stoi(
    reference: np.ndarray,
    degraded: np.ndarray,
    *,
    sample_rate_hz: int,
    stoi_fn: Callable[..., float] | None = None,
) -> float:
    implementation = stoi_fn or _resolve_stoi()
    score = float(implementation(reference, degraded, int(sample_rate_hz), extended=False))
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError("STOI devolvió un score fuera de [0, 1] o no finito.")
    return score


def compute_paired_objective_metrics(
    reference: Any,
    degraded: Any,
    *,
    sample_rate_hz: int,
    stoi_fn: Callable[..., float] | None = None,
) -> dict[str, float]:
    clean = _mono_finite_vector(reference, label="reference")
    test = _mono_finite_vector(degraded, label="degraded")
    if clean.shape != test.shape:
        raise ValueError("Las métricas pareadas requieren frame count idéntico.")
    if int(sample_rate_hz) <= 0:
        raise ValueError("sample_rate_hz debe ser positivo.")

    si_sdr = scale_invariant_sdr(clean, test)
    if not math.isfinite(si_sdr):
        raise ValueError("La baseline requiere SI-SDR finito para todos los casos noisy.")

    stoi_score = _validated_stoi(clean, test, sample_rate_hz=sample_rate_hz, stoi_fn=stoi_fn)
    return {
        "si_sdr_db": round(si_sdr, 8),
        "stoi": round(stoi_score, 8),
    }


def compute_clean_preservation_metrics(
    reference: Any,
    treated: Any,
    *,
    sample_rate_hz: int,
    stoi_fn: Callable[..., float] | None = None,
) -> dict[str, float]:
    clean = _mono_finite_vector(reference, label="reference")
    test = _mono_finite_vector(treated, label="treated")
    if clean.shape != test.shape:
        raise ValueError("Clean preservation requiere frame count idéntico.")
    if int(sample_rate_hz) <= 0:
        raise ValueError("sample_rate_hz debe ser positivo.")

    stoi_score = _validated_stoi(clean, test, sample_rate_hz=sample_rate_hz, stoi_fn=stoi_fn)
    nrmse = normalized_rmse(clean, test)
    return {
        "stoi": round(stoi_score, 8),
        "normalized_rmse": round(nrmse, 8),
    }


def build_denoise_objective_measurement(
    *,
    case_id: str,
    clean_sha256: str,
    degraded_sha256: str,
    sample_rate_hz: int,
    reference: Any,
    degraded: Any,
    stoi_fn: Callable[..., float] | None = None,
) -> dict[str, Any]:
    metrics = compute_paired_objective_metrics(
        reference,
        degraded,
        sample_rate_hz=sample_rate_hz,
        stoi_fn=stoi_fn,
    )
    return {
        "schema_version": DENOISE_OBJECTIVE_SCHEMA_VERSION,
        "record_type": DENOISE_OBJECTIVE_RECORD_TYPE,
        "policy_id": DENOISE_OBJECTIVE_POLICY_ID,
        "case_id": str(case_id),
        "clean_sha256": str(clean_sha256).lower(),
        "degraded_sha256": str(degraded_sha256).lower(),
        "sample_rate_hz": int(sample_rate_hz),
        "metrics": metrics,
        "interpretation": {
            "objective_metrics_are_auxiliary_only": True,
            "algorithm_ranking_authorized": False,
            "denoiser_selected": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }
