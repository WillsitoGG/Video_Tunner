from __future__ import annotations

import math
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from .tools import resolve_tool


class SyncDependencyError(RuntimeError):
    pass


class SyncInsufficientSignalError(RuntimeError):
    pass


@dataclass(frozen=True)
class SyncAnchor:
    video_time: float
    external_time: float
    offset_seconds: float
    score: float
    uniqueness_margin: float
    residual_seconds: float = 0.0


@dataclass(frozen=True)
class SyncEstimate:
    """Mapping from external-audio time ``u`` to video time ``t``.

    ``t = offset_seconds + time_scale * u``

    Therefore a positive offset means the external recorder started after the
    video timeline; a negative offset means it started before the video.
    """

    offset_seconds: float
    time_scale: float
    drift_ppm: float
    confidence: float
    residual_rms_seconds: float
    coarse_offset_seconds: float
    coarse_score: float
    anchors: tuple[SyncAnchor, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "offset_seconds": round(self.offset_seconds, 6),
            "time_scale": round(self.time_scale, 9),
            "drift_ppm": round(self.drift_ppm, 3),
            "confidence": round(self.confidence, 6),
            "residual_rms_seconds": round(self.residual_rms_seconds, 6),
            "coarse_offset_seconds": round(self.coarse_offset_seconds, 6),
            "coarse_score": round(self.coarse_score, 6),
            "anchors": [
                {
                    **asdict(anchor),
                    "video_time": round(anchor.video_time, 6),
                    "external_time": round(anchor.external_time, 6),
                    "offset_seconds": round(anchor.offset_seconds, 6),
                    "score": round(anchor.score, 6),
                    "uniqueness_margin": round(anchor.uniqueness_margin, 6),
                    "residual_seconds": round(anchor.residual_seconds, 6),
                }
                for anchor in self.anchors
            ],
        }


def _numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise SyncDependencyError(
            "La sincronización automática requiere NumPy. Instala `.[analysis]` "
            "o utiliza el portable con perfil de análisis."
        ) from exc
    return np


def _block_mean(values, factor: int):
    np = _numpy()
    if factor <= 1:
        return np.asarray(values, dtype=np.float64)
    values = np.asarray(values, dtype=np.float64)
    usable = (len(values) // factor) * factor
    if usable == 0:
        return np.asarray([], dtype=np.float64)
    return values[:usable].reshape(-1, factor).mean(axis=1)


def energy_envelope(
    samples: Sequence[float],
    *,
    sample_rate: int = 8000,
    envelope_rate: int = 50,
):
    """Convert mono PCM to a low-rate log-RMS envelope for mic-robust matching."""
    np = _numpy()
    if sample_rate <= 0 or envelope_rate <= 0 or envelope_rate > sample_rate:
        raise ValueError("Sample rates no válidos para sincronización.")
    values = np.asarray(samples, dtype=np.float64)
    frame = max(1, int(round(sample_rate / envelope_rate)))
    usable = (len(values) // frame) * frame
    if usable < frame * 4:
        raise SyncInsufficientSignalError("Audio demasiado corto para estimar sincronización.")
    framed = values[:usable].reshape(-1, frame)
    rms = np.sqrt(np.mean(framed * framed, axis=1) + 1e-12)
    return np.log1p(rms * 32.0)


def extract_sync_envelope(
    source: str | Path,
    raw_destination: str | Path,
    *,
    sample_rate: int = 8000,
    envelope_rate: int = 50,
):
    """Decode first audio stream to mono PCM and return a correlation envelope."""
    np = _numpy()
    source_path = Path(source)
    if not source_path.is_file():
        raise FileNotFoundError(f"No existe la fuente de audio: {source_path}")
    raw_path = Path(raw_destination)
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
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
            str(sample_rate),
            "-f",
            "s16le",
            str(raw_path),
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"FFmpeg no pudo extraer audio para sync:\n{completed.stderr}")
    samples = np.fromfile(raw_path, dtype="<i2").astype(np.float64) / 32768.0
    return energy_envelope(samples, sample_rate=sample_rate, envelope_rate=envelope_rate)


def _zncc_scores(reference, search):
    np = _numpy()
    reference = np.asarray(reference, dtype=np.float64)
    search = np.asarray(search, dtype=np.float64)
    window = len(reference)
    if window < 4 or len(search) < window:
        return np.asarray([], dtype=np.float64)
    centered = reference - reference.mean()
    reference_norm = float(np.linalg.norm(centered))
    if reference_norm < 1e-8:
        return np.asarray([], dtype=np.float64)

    dots = np.correlate(search, centered, mode="valid")
    cumulative = np.concatenate(([0.0], np.cumsum(search)))
    cumulative_sq = np.concatenate(([0.0], np.cumsum(search * search)))
    sums = cumulative[window:] - cumulative[:-window]
    sums_sq = cumulative_sq[window:] - cumulative_sq[:-window]
    variance = np.maximum(sums_sq - (sums * sums / window), 0.0)
    norms = np.sqrt(variance)
    scores = np.full_like(dots, -1.0, dtype=np.float64)
    usable = norms > 1e-8
    scores[usable] = dots[usable] / (reference_norm * norms[usable])
    return np.clip(scores, -1.0, 1.0)


def _best_match(reference, search, *, exclusion_samples: int) -> tuple[int, float, float] | None:
    np = _numpy()
    scores = _zncc_scores(reference, search)
    if len(scores) == 0:
        return None
    best_index = int(np.argmax(scores))
    best = float(scores[best_index])
    mask = np.ones(len(scores), dtype=bool)
    start = max(0, best_index - exclusion_samples)
    end = min(len(scores), best_index + exclusion_samples + 1)
    mask[start:end] = False
    second = float(np.max(scores[mask])) if bool(mask.any()) else -1.0
    return best_index, best, second


def _fit_mapping(anchors: list[tuple[float, float, float, float]]):
    np = _numpy()
    external = np.asarray([item[1] for item in anchors], dtype=np.float64)
    video = np.asarray([item[0] for item in anchors], dtype=np.float64)
    scale, intercept = np.polyfit(external, video, 1)
    residuals = video - (float(intercept) + float(scale) * external)
    return float(intercept), float(scale), residuals


def estimate_sync_from_envelopes(
    camera_envelope,
    external_envelope,
    *,
    envelope_rate: int = 50,
) -> SyncEstimate:
    """Estimate offset and clock drift from two energy envelopes.

    The estimator deliberately uses several local anchors. A single correlation
    peak is not sufficient evidence for automatic synchronization.
    """
    np = _numpy()
    camera = np.asarray(camera_envelope, dtype=np.float64)
    external = np.asarray(external_envelope, dtype=np.float64)
    if envelope_rate < 10:
        raise ValueError("envelope_rate debe ser >= 10 Hz.")
    if min(len(camera), len(external)) < envelope_rate * 4:
        raise SyncInsufficientSignalError("Audio insuficiente para sincronización automática.")
    if float(np.std(camera)) < 1e-6 or float(np.std(external)) < 1e-6:
        raise SyncInsufficientSignalError("No hay suficiente variación acústica para sincronizar.")

    camera_duration = len(camera) / envelope_rate
    external_duration = len(external) / envelope_rate
    common_duration = min(camera_duration, external_duration)

    coarse_factor = max(1, int(round(envelope_rate / 10)))
    coarse_rate = envelope_rate / coarse_factor
    coarse_camera = _block_mean(camera, coarse_factor)
    coarse_external = _block_mean(external, coarse_factor)
    coarse_window = max(4.0, min(12.0, common_duration * 0.25))
    coarse_half = coarse_window / 2.0
    coarse_options: list[tuple[float, float, float, float]] = []

    for fraction in (0.15, 0.30, 0.50, 0.70, 0.85):
        video_center = camera_duration * fraction
        if video_center - coarse_half < 0 or video_center + coarse_half > camera_duration:
            continue
        start = int(round((video_center - coarse_half) * coarse_rate))
        length = int(round(coarse_window * coarse_rate))
        reference = coarse_camera[start : start + length]
        match = _best_match(
            reference,
            coarse_external,
            exclusion_samples=max(1, int(round(0.75 * coarse_rate))),
        )
        if match is None:
            continue
        index, score, second = match
        external_center = (index + len(reference) / 2.0) / coarse_rate
        offset = video_center - external_center
        margin = max(0.0, score - second)
        quality = score + min(margin, 0.25) * 0.6
        coarse_options.append((quality, score, offset, margin))

    if not coarse_options:
        raise SyncInsufficientSignalError("No se encontró una referencia acústica utilizable.")
    coarse_options.sort(key=lambda item: item[0], reverse=True)
    _, coarse_score, coarse_offset, _ = coarse_options[0]

    anchor_window = max(3.0, min(8.0, common_duration * 0.15))
    anchor_half = anchor_window / 2.0
    search_radius = min(15.0, max(3.0, camera_duration * 0.0025))
    raw_anchors: list[tuple[float, float, float, float]] = []

    for fraction in (0.08, 0.22, 0.36, 0.50, 0.64, 0.78, 0.92):
        video_center = camera_duration * fraction
        if video_center - anchor_half < 0 or video_center + anchor_half > camera_duration:
            continue
        predicted_external = video_center - coarse_offset
        search_start_seconds = max(0.0, predicted_external - anchor_half - search_radius)
        search_end_seconds = min(
            external_duration,
            predicted_external + anchor_half + search_radius,
        )
        if search_end_seconds - search_start_seconds < anchor_window:
            continue

        reference_start = int(round((video_center - anchor_half) * envelope_rate))
        reference_length = int(round(anchor_window * envelope_rate))
        reference = camera[reference_start : reference_start + reference_length]
        search_start = int(round(search_start_seconds * envelope_rate))
        search_end = min(len(external), int(round(search_end_seconds * envelope_rate)))
        search = external[search_start:search_end]
        match = _best_match(
            reference,
            search,
            exclusion_samples=max(1, int(round(0.5 * envelope_rate))),
        )
        if match is None:
            continue
        index, score, second = match
        external_center = (search_start + index + len(reference) / 2.0) / envelope_rate
        raw_anchors.append(
            (video_center, external_center, score, max(0.0, score - second))
        )

    usable = [anchor for anchor in raw_anchors if anchor[2] >= 0.40]
    if len(usable) < 2:
        raise SyncInsufficientSignalError(
            "No hay suficientes anchors acústicos fiables para estimar offset/drift."
        )

    intercept, scale, residuals = _fit_mapping(usable)
    if len(usable) >= 4:
        median = float(np.median(residuals))
        mad = float(np.median(np.abs(residuals - median)))
        cutoff = max(0.08, 4.0 * 1.4826 * mad)
        inliers = [
            anchor for anchor, residual in zip(usable, residuals) if abs(float(residual)) <= cutoff
        ]
        if 3 <= len(inliers) < len(usable):
            usable = inliers
            intercept, scale, residuals = _fit_mapping(usable)

    residual_rms = math.sqrt(float(np.mean(residuals * residuals)))
    mean_score = float(np.mean([anchor[2] for anchor in usable]))
    mean_margin = float(np.mean([anchor[3] for anchor in usable]))
    score_component = float(np.clip((mean_score - 0.45) / 0.45, 0.0, 1.0))
    margin_component = float(np.clip(mean_margin / 0.12, 0.0, 1.0))
    residual_component = float(np.clip(1.0 - residual_rms / 0.12, 0.0, 1.0))
    count_component = float(np.clip(len(usable) / 5.0, 0.0, 1.0))
    confidence = (
        0.45 * score_component
        + 0.15 * margin_component
        + 0.25 * residual_component
        + 0.15 * count_component
    )

    anchors: list[SyncAnchor] = []
    for video_time, external_time, score, margin in usable:
        predicted = intercept + scale * external_time
        anchors.append(
            SyncAnchor(
                video_time=video_time,
                external_time=external_time,
                offset_seconds=video_time - external_time,
                score=score,
                uniqueness_margin=margin,
                residual_seconds=video_time - predicted,
            )
        )

    return SyncEstimate(
        offset_seconds=intercept,
        time_scale=scale,
        drift_ppm=(scale - 1.0) * 1_000_000.0,
        confidence=max(0.0, min(1.0, confidence)),
        residual_rms_seconds=residual_rms,
        coarse_offset_seconds=coarse_offset,
        coarse_score=coarse_score,
        anchors=tuple(anchors),
    )


def estimate_media_sync(
    video: str | Path,
    external_audio: str | Path,
    temp_dir: str | Path,
) -> SyncEstimate:
    temp = Path(temp_dir)
    temp.mkdir(parents=True, exist_ok=True)
    camera = extract_sync_envelope(video, temp / "camera_sync.s16le")
    external = extract_sync_envelope(external_audio, temp / "external_sync.s16le")
    return estimate_sync_from_envelopes(camera, external)
