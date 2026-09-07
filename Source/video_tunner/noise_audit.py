from __future__ import annotations

import json
import math
import statistics
import sys
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Any, Iterable

from .approval import sha256_path
from .audio import extract_analysis_audio

NOISE_AUDIT_SCHEMA_VERSION = 1
NOISE_AUDIT_RECORD_TYPE = "noise_evidence_audit"
QUALITY_AUDIT_RECORD_TYPE = "audiovisual_quality_audit"

NOISE_FRAME_SECONDS = 0.20
NON_SPEECH_GUARD_SECONDS = 0.15
MIN_NON_SPEECH_WINDOW_SECONDS = 0.40
MIN_NON_SPEECH_WINDOWS = 2
MIN_NON_SPEECH_TOTAL_SECONDS = 2.0


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _validate_quality_binding(
    output: Path,
    quality_audit: dict[str, Any],
    *,
    quality_audit_sha256: str,
) -> tuple[str, str]:
    audit_sha = str(quality_audit_sha256 or "").strip().lower()
    if not _valid_sha256(audit_sha):
        raise ValueError("quality_audit_sha256 debe ser un SHA-256 válido.")
    if not output.is_file():
        raise FileNotFoundError(f"No existe el output 2E a auditar: {output}")
    if not isinstance(quality_audit, dict):
        raise ValueError("Quality audit debe ser un objeto JSON.")
    if quality_audit.get("schema_version") != 1:
        raise ValueError("Quality audit schema no soportado por Phase 3.6a.")
    if quality_audit.get("record_type") != QUALITY_AUDIT_RECORD_TYPE:
        raise ValueError("Phase 3.6a requiere audiovisual_quality_audit como upstream.")
    if quality_audit.get("status") != "quality_audit_complete" or not quality_audit.get("valid"):
        raise ValueError("Noise audit requiere un quality audit completo y válido.")
    if quality_audit.get("treatment_authorized") or quality_audit.get("auto_apply"):
        raise ValueError("Quality audit upstream no puede contener capacidad de tratamiento.")

    binding = quality_audit.get("phase2e_binding")
    if not isinstance(binding, dict):
        raise ValueError("Quality audit sin binding Phase 2E.")
    if binding.get("required_status") != "technical_post_render_pass":
        raise ValueError("Noise audit sólo acepta un output 2E técnicamente PASS.")
    expected_output_sha = str(binding.get("output_sha256") or "").lower()
    if not _valid_sha256(expected_output_sha):
        raise ValueError("Quality audit sin output SHA-256 válido.")
    actual_output_sha = sha256_path(output)
    if actual_output_sha != expected_output_sha:
        raise ValueError("Output SHA-256 cambió respecto al quality audit; evidence stale.")
    return audit_sha, actual_output_sha


def _normalise_speech_intervals(
    speech_intervals: Iterable[dict[str, Any] | tuple[float, float]],
    *,
    duration: float,
) -> list[tuple[float, float]]:
    normalised: list[tuple[float, float]] = []
    for item in speech_intervals:
        if isinstance(item, dict):
            start = _finite_float(item.get("start"))
            end = _finite_float(item.get("end"))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            start = _finite_float(item[0])
            end = _finite_float(item[1])
        else:
            raise ValueError("Cada speech interval debe contener start/end.")
        if start is None or end is None or start < 0 or end <= start or end > duration + 1e-6:
            raise ValueError("Speech interval fuera de la timeline acreditada.")
        normalised.append((float(start), float(end)))

    normalised.sort()
    for previous, current in zip(normalised, normalised[1:]):
        if current[0] < previous[1] - 1e-9:
            raise ValueError("Speech intervals solapados; window evidence ambiguo.")
    return normalised


def _non_speech_windows(
    speech_intervals: list[tuple[float, float]],
    *,
    duration: float,
) -> list[tuple[float, float]]:
    expanded: list[tuple[float, float]] = []
    for start, end in speech_intervals:
        guarded = (
            max(0.0, start - NON_SPEECH_GUARD_SECONDS),
            min(duration, end + NON_SPEECH_GUARD_SECONDS),
        )
        if not expanded or guarded[0] > expanded[-1][1]:
            expanded.append(guarded)
        else:
            previous = expanded[-1]
            expanded[-1] = (previous[0], max(previous[1], guarded[1]))

    windows: list[tuple[float, float]] = []
    cursor = 0.0
    for start, end in expanded:
        if start - cursor >= MIN_NON_SPEECH_WINDOW_SECONDS:
            windows.append((cursor, start))
        cursor = max(cursor, end)
    if duration - cursor >= MIN_NON_SPEECH_WINDOW_SECONDS:
        windows.append((cursor, duration))
    return windows


def _read_pcm16_mono(path: Path) -> tuple[int, array, float]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("Noise audit requiere WAV PCM16 mono de análisis.")
        sample_rate = int(wav.getframerate())
        raw = wav.readframes(wav.getnframes())
        frame_count = int(wav.getnframes())
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder == "big":
        samples.byteswap()
    duration = frame_count / float(sample_rate) if sample_rate else 0.0
    return sample_rate, samples, duration


def _dbfs_from_linear(value: float) -> float | None:
    if value <= 0.0:
        return None
    return 20.0 * math.log10(value)


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _window_energy(
    samples: array,
    *,
    sample_rate: int,
    windows: list[tuple[float, float]],
) -> dict[str, Any]:
    frame_samples = max(1, int(round(NOISE_FRAME_SECONDS * sample_rate)))
    rms_dbfs: list[float] = []
    peak_dbfs: list[float] = []
    digital_silence_frames = 0
    total_frames = 0

    for start, end in windows:
        start_index = max(0, int(round(start * sample_rate)))
        end_index = min(len(samples), int(round(end * sample_rate)))
        cursor = start_index
        while cursor + frame_samples <= end_index:
            frame = samples[cursor : cursor + frame_samples]
            total_frames += 1
            if not frame:
                break
            square_mean = sum(float(value) * float(value) for value in frame) / len(frame)
            rms_linear = math.sqrt(square_mean) / 32768.0
            peak_linear = max(abs(int(value)) for value in frame) / 32768.0
            rms_value = _dbfs_from_linear(rms_linear)
            peak_value = _dbfs_from_linear(peak_linear)
            if rms_value is None:
                digital_silence_frames += 1
            else:
                rms_dbfs.append(rms_value)
            if peak_value is not None:
                peak_dbfs.append(peak_value)
            cursor += frame_samples

    median_rms = statistics.median(rms_dbfs) if rms_dbfs else None
    return {
        "frame_seconds": NOISE_FRAME_SECONDS,
        "frame_count": total_frames,
        "nonzero_rms_frame_count": len(rms_dbfs),
        "digital_silence_frame_count": digital_silence_frames,
        "median_rms_dbfs": None if median_rms is None else round(float(median_rms), 4),
        "p90_rms_dbfs": (
            None
            if not rms_dbfs
            else round(float(_percentile(rms_dbfs, 0.90)), 4)
        ),
        "max_peak_dbfs": None if not peak_dbfs else round(float(max(peak_dbfs)), 4),
    }


def build_noise_evidence_audit(
    output: str | Path,
    quality_audit: dict[str, Any],
    speech_intervals: Iterable[dict[str, Any] | tuple[float, float]],
    *,
    quality_audit_sha256: str,
    speech_evidence_sha256: str,
) -> dict[str, Any]:
    """Measure noise evidence on an accredited Phase 2E output without treatment.

    Speech intervals are explicit evidence supplied by an upstream timing layer.
    Phase 3.6a derives guarded non-speech windows and reports energy statistics.
    It deliberately does not classify a dBFS value as "needs denoise", choose a
    filter, authorize processing or modify media.
    """
    output_path = Path(output).resolve()
    audit_sha, output_sha = _validate_quality_binding(
        output_path,
        quality_audit,
        quality_audit_sha256=quality_audit_sha256,
    )
    speech_sha = str(speech_evidence_sha256 or "").strip().lower()
    if not _valid_sha256(speech_sha):
        raise ValueError("speech_evidence_sha256 debe ser un SHA-256 válido.")

    source_sha_before = sha256_path(output_path)
    with tempfile.TemporaryDirectory(prefix="video_tunner_noise_audit_") as temp:
        wav_path = Path(temp) / "phase3_noise_analysis.wav"
        extract_analysis_audio(output_path, wav_path, sample_rate=16000)
        sample_rate, samples, duration = _read_pcm16_mono(wav_path)

    if sha256_path(output_path) != source_sha_before:
        raise RuntimeError("Noise audit alteró el output acreditado; abortado.")
    if sample_rate != 16000:
        raise ValueError("Noise audit esperaba exactamente 16 kHz en el WAV de análisis.")
    if duration <= 0.0 or not samples:
        raise ValueError("Noise audit no obtuvo audio PCM medible.")

    speech = _normalise_speech_intervals(speech_intervals, duration=duration)
    non_speech = _non_speech_windows(speech, duration=duration)
    speech_seconds = sum(end - start for start, end in speech)
    non_speech_seconds = sum(end - start for start, end in non_speech)

    non_speech_energy = _window_energy(
        samples,
        sample_rate=sample_rate,
        windows=non_speech,
    )
    speech_energy = _window_energy(
        samples,
        sample_rate=sample_rate,
        windows=speech,
    )

    evidence_sufficient = (
        len(non_speech) >= MIN_NON_SPEECH_WINDOWS
        and non_speech_seconds >= MIN_NON_SPEECH_TOTAL_SECONDS
        and non_speech_energy["frame_count"] > 0
    )

    speech_median = speech_energy.get("median_rms_dbfs")
    noise_median = non_speech_energy.get("median_rms_dbfs")
    energy_delta = (
        None
        if speech_median is None or noise_median is None
        else round(float(speech_median) - float(noise_median), 4)
    )

    return {
        "schema_version": NOISE_AUDIT_SCHEMA_VERSION,
        "record_type": NOISE_AUDIT_RECORD_TYPE,
        "status": "noise_measurement_complete" if evidence_sufficient else "insufficient_noise_evidence",
        "valid": True,
        "evidence_sufficient": evidence_sufficient,
        "quality_binding": {
            "quality_audit_sha256": audit_sha,
            "required_quality_status": "quality_audit_complete",
            "output_sha256": output_sha,
        },
        "window_evidence": {
            "speech_evidence_sha256": speech_sha,
            "basis": "explicit_speech_intervals_on_accredited_phase2e_output",
            "speech_intervals": [
                {"start": round(start, 6), "end": round(end, 6)}
                for start, end in speech
            ],
            "non_speech_guard_seconds": NON_SPEECH_GUARD_SECONDS,
            "minimum_non_speech_window_seconds": MIN_NON_SPEECH_WINDOW_SECONDS,
            "derived_non_speech_windows": [
                {"start": round(start, 6), "end": round(end, 6)}
                for start, end in non_speech
            ],
        },
        "coverage": {
            "duration_seconds": round(duration, 6),
            "speech_window_count": len(speech),
            "speech_seconds": round(speech_seconds, 6),
            "non_speech_window_count": len(non_speech),
            "non_speech_seconds": round(non_speech_seconds, 6),
            "minimum_non_speech_windows_required": MIN_NON_SPEECH_WINDOWS,
            "minimum_non_speech_seconds_required": MIN_NON_SPEECH_TOTAL_SECONDS,
        },
        "measurements": {
            "non_speech_energy": non_speech_energy,
            "speech_energy": speech_energy,
            "speech_to_non_speech_median_rms_delta_db": energy_delta,
        },
        "interpretation": {
            "metric_scope": "energy evidence only",
            "snr_note": "speech_to_non_speech_median_rms_delta_db is an energy proxy, not a perceptual SNR estimate.",
            "threshold_note": "No measured dBFS value in schema v1 is a denoise threshold.",
            "insufficient_note": "Insufficient evidence means more reliable non-speech coverage is required; it is not evidence that denoise is needed.",
        },
        "treatment_policy": {
            "denoise_evaluated": False,
            "denoise_authorized": False,
            "filter_selected": False,
            "parameters_defined": False,
            "normalization_authorized": False,
            "join_smoothing_authorized": False,
            "reason": "Phase 3.6a is measurement-only. Denoise requires a separate corpus, decision and authorization chain.",
        },
        "executable": False,
        "treatment_authorized": False,
        "auto_apply": False,
    }


def save_noise_evidence_audit(report: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
