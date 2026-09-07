from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

from .approval import sha256_path
from .tools import resolve_tool

AUDIOVISUAL_QUALITY_SCHEMA_VERSION = 1
AUDIOVISUAL_QUALITY_RECORD_TYPE = "audiovisual_quality_audit"
TECHNICAL_VERIFICATION_RECORD_TYPE = "semantic_render_verification"
TRUE_PEAK_RISK_DBTP = 0.0


_LOUDNORM_JSON = re.compile(
    r"\{\s*\"input_i\"\s*:.*?\"target_offset\"\s*:\s*\"[^\"]+\"\s*\}",
    re.DOTALL,
)


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _finite_float(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def parse_loudnorm_measurement(stderr: str) -> dict[str, float | None]:
    """Parse FFmpeg loudnorm JSON input measurements without applying treatment."""
    matches = list(_LOUDNORM_JSON.finditer(stderr))
    if not matches:
        raise ValueError("FFmpeg loudnorm no devolvió un bloque JSON de medición.")
    payload = json.loads(matches[-1].group(0))
    required = ("input_i", "input_tp", "input_lra", "input_thresh")
    if any(key not in payload for key in required):
        raise ValueError("FFmpeg loudnorm devolvió una medición incompleta.")
    return {
        "integrated_lufs": _finite_float(payload["input_i"]),
        "true_peak_dbtp": _finite_float(payload["input_tp"]),
        "loudness_range_lu": _finite_float(payload["input_lra"]),
        "threshold_lufs": _finite_float(payload["input_thresh"]),
    }


def measure_audio_loudness(source: str | Path) -> dict[str, float | None]:
    """Measure the first audio stream with FFmpeg loudnorm in analysis-only mode."""
    path = Path(source)
    if not path.is_file():
        raise FileNotFoundError(f"No existe el media a medir: {path}")
    ffmpeg = resolve_tool("ffmpeg")
    completed = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-af",
            "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "FFmpeg no pudo medir loudness/true peak para Phase 3:\n"
            f"{completed.stderr}"
        )
    measurement = parse_loudnorm_measurement(completed.stderr)
    if measurement["integrated_lufs"] is None or measurement["true_peak_dbtp"] is None:
        raise ValueError("La medición loudness/true peak no es finita; quality audit fail-safe.")
    return measurement


def _validate_phase2e_input(
    source: Path,
    output: Path,
    technical_report: dict[str, Any],
    *,
    technical_report_sha256: str,
) -> tuple[str, str, str]:
    """Bind Phase 3 strictly to an already-passing immutable Phase 2E output."""
    report_sha = technical_report_sha256.strip().lower()
    if not _valid_sha256(report_sha):
        raise ValueError("technical_report_sha256 debe ser un SHA-256 válido.")
    if source.resolve() == output.resolve():
        raise ValueError("Phase 3 no puede auditar source y output como el mismo archivo.")
    if not source.is_file():
        raise FileNotFoundError(f"No existe el source original: {source}")
    if not output.is_file():
        raise FileNotFoundError(f"No existe el output 2E: {output}")
    if not isinstance(technical_report, dict):
        raise ValueError("El technical report 2E no es un objeto JSON.")
    if technical_report.get("schema_version") != 1:
        raise ValueError("Technical verification schema no soportado por Phase 3.1.")
    if technical_report.get("record_type") != TECHNICAL_VERIFICATION_RECORD_TYPE:
        raise ValueError("Phase 3 requiere semantic_render_verification como upstream.")
    if (
        technical_report.get("status") != "technical_post_render_pass"
        or not technical_report.get("technical_pass")
        or technical_report.get("blockers") not in ([], None)
    ):
        raise ValueError("Phase 3 no puede rescatar un render que no tenga technical_post_render_pass.")
    if technical_report.get("auto_apply"):
        raise ValueError("El technical report upstream no puede habilitar auto_apply.")

    source_record = technical_report.get("source")
    output_record = technical_report.get("output")
    joins = technical_report.get("post_render_join_audits")
    if not isinstance(source_record, dict) or not isinstance(output_record, dict):
        raise ValueError("Technical report sin provenance source/output.")
    if not isinstance(joins, list) or not joins:
        raise ValueError("Phase 3.1 requiere al menos un join 2E técnicamente auditado.")
    if any(not isinstance(join, dict) or not join.get("technical_pass") for join in joins):
        raise ValueError("Phase 3 no puede rescatar joins que hayan fallado el gate técnico 2E.")

    expected_source_sha = str(source_record.get("sha256") or "").lower()
    expected_output_sha = str(output_record.get("sha256") or "").lower()
    if not _valid_sha256(expected_source_sha) or not _valid_sha256(expected_output_sha):
        raise ValueError("Technical report sin SHA-256 source/output válido.")
    actual_source_sha = sha256_path(source)
    actual_output_sha = sha256_path(output)
    if actual_source_sha != expected_source_sha:
        raise ValueError("Source SHA-256 no coincide con la evidencia 2E.")
    if actual_output_sha != expected_output_sha:
        raise ValueError("Output SHA-256 no coincide con la evidencia 2E.")
    return report_sha, actual_source_sha, actual_output_sha


def _measurement_delta(
    source: dict[str, float | None],
    output: dict[str, float | None],
) -> dict[str, float | None]:
    source_i = source.get("integrated_lufs")
    output_i = output.get("integrated_lufs")
    source_tp = source.get("true_peak_dbtp")
    output_tp = output.get("true_peak_dbtp")
    return {
        "integrated_loudness_delta_lu": (
            None
            if source_i is None or output_i is None
            else round(float(output_i) - float(source_i), 4)
        ),
        "true_peak_delta_db": (
            None
            if source_tp is None or output_tp is None
            else round(float(output_tp) - float(source_tp), 4)
        ),
    }


def build_audiovisual_quality_audit(
    source: str | Path,
    output: str | Path,
    technical_report: dict[str, Any],
    *,
    technical_report_sha256: str,
) -> dict[str, Any]:
    """Build Phase 3.1 measurement evidence without changing the rendered media.

    This is deliberately audit-only. It establishes measurable loudness/true-peak
    evidence before normalization, denoise or join treatment policies are chosen.
    A Phase 3 signal can never make failed Phase 2E evidence acceptable.
    """
    source_path = Path(source).resolve()
    output_path = Path(output).resolve()
    report_sha, source_sha, output_sha = _validate_phase2e_input(
        source_path,
        output_path,
        technical_report,
        technical_report_sha256=technical_report_sha256,
    )

    source_audio = measure_audio_loudness(source_path)
    output_audio = measure_audio_loudness(output_path)
    delta = _measurement_delta(source_audio, output_audio)

    findings: list[dict[str, Any]] = []
    output_true_peak = output_audio.get("true_peak_dbtp")
    if output_true_peak is not None and float(output_true_peak) > TRUE_PEAK_RISK_DBTP:
        findings.append(
            {
                "code": "output_true_peak_above_0_dbtp",
                "severity": "risk",
                "measured_dbtp": float(output_true_peak),
                "threshold_dbtp": TRUE_PEAK_RISK_DBTP,
                "rationale": "El output supera 0 dBTP; se registra como riesgo de true-peak, no como autorización para normalizar.",
            }
        )

    return {
        "schema_version": AUDIOVISUAL_QUALITY_SCHEMA_VERSION,
        "record_type": AUDIOVISUAL_QUALITY_RECORD_TYPE,
        "status": "quality_audit_complete",
        "valid": True,
        "phase2e_binding": {
            "required_status": "technical_post_render_pass",
            "technical_report_sha256": report_sha,
            "source_sha256": source_sha,
            "output_sha256": output_sha,
            "join_count": len(technical_report.get("post_render_join_audits") or []),
        },
        "measurements": {
            "source_audio": source_audio,
            "output_audio": output_audio,
            "delta": delta,
        },
        "findings": findings,
        "summary": {
            "finding_count": len(findings),
            "risk_count": sum(item.get("severity") == "risk" for item in findings),
            "quality_review_required": bool(findings),
        },
        "treatment_policy": {
            "normalization_evaluated": False,
            "normalization_authorized": False,
            "denoise_evaluated": False,
            "denoise_authorized": False,
            "join_smoothing_evaluated": False,
            "join_smoothing_authorized": False,
            "reason": "Phase 3.1 is measurement-only; treatment targets require separate precommitted evidence.",
        },
        "treatment_authorized": False,
        "auto_apply": False,
    }


def save_audiovisual_quality_audit(
    report: dict[str, Any], destination: str | Path
) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
