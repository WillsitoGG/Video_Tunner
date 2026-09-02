from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .media import probe_media
from .sync import SyncEstimate, SyncInsufficientSignalError, estimate_media_sync
from .tools import resolve_tool

AUTO_MIN_CONFIDENCE = 0.65
AUTO_MIN_ANCHORS = 3
AUTO_MAX_RESIDUAL_SECONDS = 0.08
AUTO_MAX_ABS_DRIFT_PPM = 2000.0
AUTO_MIN_COVERAGE_RATIO = 0.98
AUTO_MAX_UNCOVERED_EDGE_SECONDS = 5.0


def _sha256_file(source: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(source).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def coverage_metrics(
    *,
    video_duration: float,
    external_duration: float,
    offset_seconds: float,
    time_scale: float,
) -> dict[str, float]:
    if video_duration <= 0 or external_duration <= 0 or time_scale <= 0:
        raise ValueError("Duraciones/time_scale no válidos para calcular cobertura.")
    mapped_start = offset_seconds
    mapped_end = offset_seconds + time_scale * external_duration
    overlap_start = max(0.0, mapped_start)
    overlap_end = min(video_duration, mapped_end)
    overlap = max(0.0, overlap_end - overlap_start)
    return {
        "mapped_start_video_seconds": round(mapped_start, 6),
        "mapped_end_video_seconds": round(mapped_end, 6),
        "covered_seconds": round(overlap, 6),
        "coverage_ratio": round(overlap / video_duration, 6),
        "uncovered_start_seconds": round(max(0.0, mapped_start), 6),
        "uncovered_end_seconds": round(max(0.0, video_duration - mapped_end), 6),
    }


def evaluate_auto_sync(
    estimate: SyncEstimate,
    coverage: dict[str, float],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if estimate.confidence < AUTO_MIN_CONFIDENCE:
        reasons.append(
            f"confidence {estimate.confidence:.3f} < {AUTO_MIN_CONFIDENCE:.2f}"
        )
    if len(estimate.anchors) < AUTO_MIN_ANCHORS:
        reasons.append(f"anchors {len(estimate.anchors)} < {AUTO_MIN_ANCHORS}")
    if estimate.residual_rms_seconds > AUTO_MAX_RESIDUAL_SECONDS:
        reasons.append(
            "residual RMS "
            f"{estimate.residual_rms_seconds:.3f}s > {AUTO_MAX_RESIDUAL_SECONDS:.2f}s"
        )
    if abs(estimate.drift_ppm) > AUTO_MAX_ABS_DRIFT_PPM:
        reasons.append(
            f"drift {estimate.drift_ppm:.1f}ppm excede ±{AUTO_MAX_ABS_DRIFT_PPM:.0f}ppm"
        )
    if coverage["coverage_ratio"] < AUTO_MIN_COVERAGE_RATIO:
        reasons.append(
            f"coverage {coverage['coverage_ratio']:.3f} < {AUTO_MIN_COVERAGE_RATIO:.2f}"
        )
    if coverage["uncovered_start_seconds"] > AUTO_MAX_UNCOVERED_EDGE_SECONDS:
        reasons.append(
            "inicio externo sin cobertura "
            f"{coverage['uncovered_start_seconds']:.2f}s > {AUTO_MAX_UNCOVERED_EDGE_SECONDS:.1f}s"
        )
    if coverage["uncovered_end_seconds"] > AUTO_MAX_UNCOVERED_EDGE_SECONDS:
        reasons.append(
            "final externo sin cobertura "
            f"{coverage['uncovered_end_seconds']:.2f}s > {AUTO_MAX_UNCOVERED_EDGE_SECONDS:.1f}s"
        )
    return not reasons, reasons


def _run_ffmpeg(command: list[str], *, failure_message: str) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"{failure_message}:\n{completed.stderr}")


def materialize_embedded_master(
    video: str | Path,
    destination: str | Path,
) -> Path:
    video_path = Path(video)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    _run_ffmpeg(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-map",
            "0:a:0",
            "-vn",
            "-ar",
            "48000",
            "-c:a",
            "flac",
            str(destination_path),
        ],
        failure_message="FFmpeg no pudo materializar el master audio embebido",
    )
    if not destination_path.is_file() or destination_path.stat().st_size == 0:
        raise RuntimeError("No se generó un master audio embebido válido.")
    return destination_path


def external_alignment_filter(
    *,
    offset_seconds: float,
    time_scale: float,
    video_duration: float,
) -> str:
    """Build an audio filter whose sample timeline is exactly the video timeline.

    FFmpeg's ``atrim`` does not rewrite timestamps. In addition, an indefinite
    ``apad`` followed by timestamp-based trimming can leave container duration
    shorter than the intended sample timeline. Regenerate audio PTS from sample
    count, request an explicit minimum padded duration, then cap by duration.
    """
    if time_scale <= 0:
        raise ValueError("time_scale debe ser positivo.")
    if video_duration <= 0:
        raise ValueError("video_duration debe ser positivo.")
    tempo = 1.0 / time_scale
    if tempo < 0.5 or tempo > 2.0:
        raise ValueError("La corrección de drift solicitada excede el rango seguro de atempo.")

    filters = [
        f"atempo={tempo:.12f}",
        "asetpts=N/SR/TB",
    ]
    if offset_seconds >= 0:
        delay_ms = max(0, int(round(offset_seconds * 1000.0)))
        if delay_ms:
            filters.append(f"adelay={delay_ms}:all=1")
    else:
        filters.append(f"atrim=start={-offset_seconds:.9f}")

    # Treat all upstream timing as samples from this point onward. This keeps
    # inserted silence (positive offset) and removes preroll (negative offset)
    # while making the final FLAC start at PTS zero.
    filters.extend(
        [
            "asetpts=N/SR/TB",
            f"apad=whole_dur={video_duration:.9f}",
            f"atrim=duration={video_duration:.9f}",
            "asetpts=N/SR/TB",
        ]
    )
    return ",".join(filters)


def materialize_external_master(
    external_audio: str | Path,
    destination: str | Path,
    *,
    video_duration: float,
    offset_seconds: float,
    time_scale: float,
) -> Path:
    source_path = Path(external_audio)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = resolve_tool("ffmpeg")
    filter_chain = external_alignment_filter(
        offset_seconds=offset_seconds,
        time_scale=time_scale,
        video_duration=video_duration,
    )
    _run_ffmpeg(
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
            "-af",
            filter_chain,
            "-t",
            f"{video_duration:.9f}",
            "-ar",
            "48000",
            "-c:a",
            "flac",
            str(destination_path),
        ],
        failure_message="FFmpeg no pudo materializar el master audio externo sincronizado",
    )
    if not destination_path.is_file() or destination_path.stat().st_size == 0:
        raise RuntimeError("No se generó un master audio externo válido.")
    return destination_path


def _source_metadata(path: Path, probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "file": path.name,
        "duration_seconds": probe["duration_seconds"],
        "audio_streams": probe["audio_streams"],
        "video_streams": probe["video_streams"],
        "sha256": _sha256_file(path),
    }


def _write_report(report: dict[str, Any], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination


def ingest_video(
    video: str | Path,
    output_dir: str | Path,
    *,
    external_audio: str | Path | None = None,
    manual_offset_seconds: float | None = None,
    manual_drift_ppm: float = 0.0,
) -> dict[str, Any]:
    """Resolve a video + optional external-audio input into an auditable master audio.

    Automatic external sync never materializes a master when confidence/coverage
    checks fail. Manual offset is an explicit override and may materialize partial
    coverage; uncovered regions are silence, never an implicit camera-audio mix.
    """
    video_path = Path(video)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    video_probe = probe_media(video_path)
    if video_probe["video_streams"] < 1:
        raise ValueError("La entrada principal debe contener vídeo.")

    stem = video_path.stem
    master_path = output_root / f"{stem}_master_audio.flac"
    report_path = output_root / f"{stem}_ingest.json"
    base_report: dict[str, Any] = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "video": _source_metadata(video_path, video_probe),
        "timeline_convention": (
            "video_time = offset_seconds + time_scale * external_time; "
            "positive offset => external recorder started after video"
        ),
    }

    if external_audio is None:
        if manual_offset_seconds is not None or manual_drift_ppm != 0.0:
            raise ValueError("Offset/drift manual sólo aplica cuando existe audio externo.")
        if video_probe["audio_streams"] < 1:
            raise ValueError("El vídeo no contiene audio embebido y no se indicó audio externo.")
        master = materialize_embedded_master(video_path, master_path)
        report = {
            **base_report,
            "input_mode": "embedded_audio",
            "status": "ready",
            "external_audio": None,
            "sync": {"method": "embedded", "required": False},
            "master_audio": {"file": master.name, "source": "embedded_audio"},
            "warnings": [],
        }
        saved = _write_report(report, report_path)
        return {"master_audio": str(master), "ingest_report": str(saved), "status": "ready"}

    external_path = Path(external_audio)
    external_probe = probe_media(external_path)
    if external_probe["audio_streams"] < 1:
        raise ValueError("La entrada de audio externo no contiene una pista de audio.")
    base_report["external_audio"] = _source_metadata(external_path, external_probe)

    if manual_offset_seconds is not None:
        time_scale = 1.0 + manual_drift_ppm / 1_000_000.0
        if time_scale <= 0:
            raise ValueError("El drift manual produce un time_scale no válido.")
        coverage = coverage_metrics(
            video_duration=float(video_probe["duration_seconds"]),
            external_duration=float(external_probe["duration_seconds"]),
            offset_seconds=manual_offset_seconds,
            time_scale=time_scale,
        )
        warnings: list[str] = []
        if coverage["coverage_ratio"] < AUTO_MIN_COVERAGE_RATIO:
            warnings.append(
                "Cobertura externa parcial: los tramos no cubiertos se rellenan con silencio; "
                "no se mezcla audio de cámara de forma implícita."
            )
        master = materialize_external_master(
            external_path,
            master_path,
            video_duration=float(video_probe["duration_seconds"]),
            offset_seconds=manual_offset_seconds,
            time_scale=time_scale,
        )
        report = {
            **base_report,
            "input_mode": "external_audio",
            "status": "ready_manual",
            "sync": {
                "method": "manual_override",
                "offset_seconds": round(manual_offset_seconds, 6),
                "time_scale": round(time_scale, 9),
                "drift_ppm": round(manual_drift_ppm, 3),
                "confidence": None,
                "anchors": [],
            },
            "coverage": coverage,
            "master_audio": {"file": master.name, "source": "external_audio"},
            "warnings": warnings,
        }
        saved = _write_report(report, report_path)
        return {
            "master_audio": str(master),
            "ingest_report": str(saved),
            "status": "ready_manual",
        }

    if manual_drift_ppm != 0.0:
        raise ValueError("--drift-ppm requiere también un --offset manual.")
    if video_probe["audio_streams"] < 1:
        raise ValueError(
            "No hay audio de cámara para auto-sync. Usa un offset manual; Video_Tunner no adivina."
        )

    try:
        with tempfile.TemporaryDirectory(prefix=".video_tunner_sync_", dir=output_root) as temp:
            estimate = estimate_media_sync(video_path, external_path, temp)
    except SyncInsufficientSignalError as exc:
        reason = str(exc)
        report = {
            **base_report,
            "input_mode": "external_audio",
            "status": "review_required",
            "sync": {"method": "auto_correlation", "estimate": None},
            "coverage": None,
            "master_audio": None,
            "review_reasons": [reason],
            "warnings": ["Auto-sync no aplicado: evidencia acústica insuficiente."],
        }
        saved = _write_report(report, report_path)
        return {
            "master_audio": None,
            "ingest_report": str(saved),
            "status": "review_required",
            "review_reasons": [reason],
        }

    coverage = coverage_metrics(
        video_duration=float(video_probe["duration_seconds"]),
        external_duration=float(external_probe["duration_seconds"]),
        offset_seconds=estimate.offset_seconds,
        time_scale=estimate.time_scale,
    )
    accepted, reasons = evaluate_auto_sync(estimate, coverage)

    if not accepted:
        report = {
            **base_report,
            "input_mode": "external_audio",
            "status": "review_required",
            "sync": {"method": "auto_correlation", **estimate.to_dict()},
            "coverage": coverage,
            "master_audio": None,
            "review_reasons": reasons,
            "warnings": ["Auto-sync no aplicado: se requiere revisión/offset manual."],
        }
        saved = _write_report(report, report_path)
        return {
            "master_audio": None,
            "ingest_report": str(saved),
            "status": "review_required",
            "review_reasons": reasons,
        }

    master = materialize_external_master(
        external_path,
        master_path,
        video_duration=float(video_probe["duration_seconds"]),
        offset_seconds=estimate.offset_seconds,
        time_scale=estimate.time_scale,
    )
    report = {
        **base_report,
        "input_mode": "external_audio",
        "status": "ready_auto",
        "sync": {"method": "auto_correlation", **estimate.to_dict()},
        "coverage": coverage,
        "master_audio": {"file": master.name, "source": "external_audio"},
        "review_reasons": [],
        "warnings": [],
    }
    saved = _write_report(report, report_path)
    return {"master_audio": str(master), "ingest_report": str(saved), "status": "ready_auto"}
