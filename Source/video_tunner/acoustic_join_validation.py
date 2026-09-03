from __future__ import annotations

import math
from collections import Counter
from typing import Any

from .acoustic_join import (
    SAMPLE_RATE,
    assess_join_edge_samples,
    build_acoustic_join_assessments,
)

RISK_STATUSES = {
    "level_discontinuity_risk",
    "waveform_discontinuity_risk",
    "combined_discontinuity_risk",
    "insufficient_audio_context",
    "blocked_by_context",
}


def _np():
    try:
        import numpy as np
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Acoustic join validation requires NumPy.") from exc
    return np


def _join(*, context_status: str = "join_context_only") -> dict[str, Any]:
    return {
        "id": "join-assessment-0001",
        "candidate_id": "possible_filler-0001",
        "candidate_kind": "possible_filler",
        "status": context_status,
        "target_span": {"start": 1.0, "end": 1.2, "text": "eh"},
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def _sine(*, amplitude: float, seconds: float = 0.08, frequency: float = 220.0):
    np = _np()
    count = int(round(SAMPLE_RATE * seconds))
    t = np.arange(count, dtype=np.float32) / SAMPLE_RATE
    return (amplitude * np.sin(2.0 * math.pi * frequency * t)).astype(np.float32)


def _samples(pattern: str):
    np = _np()
    count = int(round(SAMPLE_RATE * 0.08))

    if pattern == "continuous_sine":
        full = _sine(amplitude=0.35, seconds=0.16)
        half = len(full) // 2
        return full[:half], full[half:]
    if pattern == "low_energy":
        zeros = np.zeros(count, dtype=np.float32)
        return zeros, zeros.copy()
    if pattern == "level_delta":
        return _sine(amplitude=0.05), _sine(amplitude=0.8)
    if pattern == "waveform_step":
        return (
            np.full(count, 0.4, dtype=np.float32),
            np.full(count, -0.4, dtype=np.float32),
        )
    if pattern == "combined_risk":
        left = _sine(amplitude=0.05)
        right = _sine(amplitude=0.8)
        left[-1] = 0.8
        right[0] = -0.8
        return left, right
    if pattern == "acceptable_level_delta":
        return _sine(amplitude=0.2), _sine(amplitude=0.6)
    if pattern == "small_waveform_step":
        return (
            np.full(count, 0.1, dtype=np.float32),
            np.full(count, -0.1, dtype=np.float32),
        )
    if pattern == "low_energy_step":
        return (
            np.full(count, 0.001, dtype=np.float32),
            np.full(count, -0.001, dtype=np.float32),
        )
    if pattern == "empty_left":
        return np.array([], dtype=np.float32), np.ones(count, dtype=np.float32) * 0.2
    raise ValueError(f"Unknown acoustic benchmark pattern: {pattern}")


def evaluate_acoustic_join_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    expected_counter: Counter[str] = Counter()
    actual_counter: Counter[str] = Counter()
    metrics: dict[str, Any] = {
        "cases": len(cases),
        "status_mismatches": 0,
        "measurement_mismatches": 0,
        "safety_violations": 0,
        "expected_risk_cases": 0,
        "risk_cases_correct": 0,
        "expected_status_counts": {},
        "actual_status_counts": {},
    }

    for case in cases:
        context_status = str(case.get("context_status") or "join_context_only")
        join = _join(context_status=context_status)
        if context_status != "join_context_only":
            assessment = build_acoustic_join_assessments(
                "intentionally-missing-master.wav",
                [join],
            )[0]
        else:
            left, right = _samples(str(case["pattern"]))
            assessment = assess_join_edge_samples(join, left, right)

        expected_status = str(case["expected_status"])
        actual_status = str(assessment.get("status"))
        expected_measurement = bool(case.get("expected_measurement"))
        actual_measurement = bool(assessment.get("measurement_available"))
        expected_counter.update([expected_status])
        actual_counter.update([actual_status])

        if expected_status != actual_status:
            metrics["status_mismatches"] += 1
        if expected_measurement != actual_measurement:
            metrics["measurement_mismatches"] += 1
        if assessment.get("safe_for_cut") or assessment.get("executable") or assessment.get("auto_apply"):
            metrics["safety_violations"] += 1

        if expected_status in RISK_STATUSES:
            metrics["expected_risk_cases"] += 1
            if actual_status == expected_status:
                metrics["risk_cases_correct"] += 1

        details.append(
            {
                "id": case.get("id"),
                "source_type": case.get("source_type"),
                "expected_status": expected_status,
                "actual_status": actual_status,
                "expected_measurement": expected_measurement,
                "actual_measurement": actual_measurement,
                "safe_for_cut": bool(assessment.get("safe_for_cut")),
                "executable": bool(assessment.get("executable")),
                "auto_apply": bool(assessment.get("auto_apply")),
                "metrics": assessment.get("metrics"),
            }
        )

    metrics["expected_status_counts"] = dict(sorted(expected_counter.items()))
    metrics["actual_status_counts"] = dict(sorted(actual_counter.items()))
    metrics["status_accuracy"] = (
        (metrics["cases"] - metrics["status_mismatches"]) / metrics["cases"]
        if metrics["cases"]
        else 1.0
    )
    metrics["risk_recall"] = (
        metrics["risk_cases_correct"] / metrics["expected_risk_cases"]
        if metrics["expected_risk_cases"]
        else 1.0
    )
    return {"metrics": metrics, "cases": details}


def acoustic_join_gate(report: dict[str, Any]) -> dict[str, Any]:
    metrics = report["metrics"]
    checks = {
        "status_exactness": metrics["status_mismatches"] == 0
        and metrics["status_accuracy"] == 1.0,
        "measurement_contract": metrics["measurement_mismatches"] == 0,
        "risk_detection": metrics["risk_recall"] == 1.0,
        "non_executable": metrics["safety_violations"] == 0,
    }
    return {"passed": all(checks.values()), "checks": checks}
