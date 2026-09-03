from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .candidates import build_analysis_report, build_candidates, save_analysis_report, sha256_file
from .correction_scope import build_correction_scopes
from .correction_scope_report import attach_correction_scopes
from .edit_plan import MODE_SETTINGS
from .filler_context import build_filler_assessments
from .filler_context_report import attach_filler_assessments
from .ingest import ingest_video
from .join_safety import build_join_assessments
from .join_safety_report import attach_join_assessments
from .media import probe_media
from .semantic_candidates import build_semantic_candidates
from .semantic_decisions import build_semantic_decisions
from .semantic_report import attach_semantic_decisions
from .transcription import (
    transcribe_audio,
    write_srt,
    write_transcript_json,
    write_transcript_txt,
)
from .vad import detect_speech

MASTER_DURATION_TOLERANCE_SECONDS = 0.15
READY_INGEST_STATUSES = {"ready", "ready_auto", "ready_manual"}


def _load_ingest_report(path: str | Path) -> dict[str, Any]:
    report_path = Path(path)
    if not report_path.is_file():
        raise FileNotFoundError(f"No existe el ingest report: {report_path}")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("El ingest report no contiene un objeto JSON válido.")
    return payload


def _validate_master_timeline(
    source_path: Path,
    source_probe: dict[str, Any],
    master_path: Path,
    master_probe: dict[str, Any],
) -> None:
    if master_probe.get("audio_streams", 0) < 1:
        raise ValueError("El master audio no contiene una pista de audio analizable.")
    source_duration = float(source_probe["duration_seconds"])
    master_duration = float(master_probe["duration_seconds"])
    if abs(master_duration - source_duration) > MASTER_DURATION_TOLERANCE_SECONDS:
        raise ValueError(
            "El master audio no coincide con la timeline del vídeo: "
            f"video={source_duration:.3f}s master={master_duration:.3f}s."
        )
    if not master_path.is_file():
        raise FileNotFoundError(f"No existe el master audio: {master_path}")


def _validate_ingest_provenance(
    source_path: Path,
    master_path: Path,
    ingest_report: dict[str, Any],
) -> None:
    if ingest_report.get("status") not in READY_INGEST_STATUSES:
        raise ValueError(
            "El ingest report no acredita un master listo para análisis: "
            f"status={ingest_report.get('status')!r}."
        )

    video_block = ingest_report.get("video") or {}
    expected_source_hash = video_block.get("sha256")
    if not expected_source_hash:
        raise ValueError("El ingest report no contiene SHA-256 del vídeo fuente.")
    actual_source_hash = sha256_file(source_path)
    if actual_source_hash != expected_source_hash:
        raise ValueError("El ingest report pertenece a un vídeo fuente diferente.")

    master_block = ingest_report.get("master_audio") or {}
    expected_master_file = master_block.get("file")
    if expected_master_file and expected_master_file != master_path.name:
        raise ValueError(
            "El master audio indicado no coincide con el registrado en ingest.json."
        )


def _append_semantic_candidates(
    candidates: list[dict[str, Any]],
    semantic_candidates: list[dict[str, Any]],
) -> None:
    """Append semantic candidates with stable IDs; never turn them into edits."""
    counters: dict[str, int] = {}
    for candidate in semantic_candidates:
        kind = str(candidate["kind"])
        counters[kind] = counters.get(kind, 0) + 1
        candidate["id"] = f"{kind}-{counters[kind]:04d}"
        candidate["auto_apply"] = False
        candidate["decision"] = "undecided"
        candidates.append(candidate)
    candidates.sort(key=lambda item: (float(item["start"]), float(item["end"]), item["kind"]))


def analyze_spoken_video(
    source: str | Path,
    output_dir: str | Path,
    *,
    mode: str = "conservative",
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
    external_audio: str | Path | None = None,
    manual_offset_seconds: float | None = None,
    manual_drift_ppm: float = 0.0,
    master_audio: str | Path | None = None,
    ingest_report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve master audio and emit separate non-executable evidence layers.

    Whisper and Silero VAD consume the same master audio. All timestamps remain
    on the video timeline. Candidates, correction scopes, filler assessments,
    join assessments and semantic decisions are deliberately separate and never
    become executable edits in this phase.
    """
    if mode not in MODE_SETTINGS:
        raise ValueError(f"Modo desconocido: {mode}")

    source_path = Path(source)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    source_probe = probe_media(source_path)
    if source_probe.get("video_streams", 0) < 1:
        raise ValueError("La entrada principal de analyze debe contener vídeo.")

    if master_audio is not None:
        if external_audio is not None or manual_offset_seconds is not None or manual_drift_ppm != 0.0:
            raise ValueError(
                "--master-audio no puede combinarse con --audio/--offset/--drift-ppm; "
                "el master ya debe estar resuelto."
            )
        if ingest_report_path is None:
            raise ValueError(
                "Un --master-audio pre-resuelto requiere también --ingest-report para verificar procedencia."
            )
        master_path = Path(master_audio)
        master_probe = probe_media(master_path)
        ingest_path = Path(ingest_report_path)
        ingest_report = _load_ingest_report(ingest_path)
        _validate_master_timeline(source_path, source_probe, master_path, master_probe)
        _validate_ingest_provenance(source_path, master_path, ingest_report)
    else:
        if ingest_report_path is not None:
            raise ValueError("--ingest-report sólo puede usarse junto con --master-audio.")
        ingest_result = ingest_video(
            source_path,
            output_root,
            external_audio=external_audio,
            manual_offset_seconds=manual_offset_seconds,
            manual_drift_ppm=manual_drift_ppm,
        )
        ingest_path = Path(ingest_result["ingest_report"])
        if ingest_result["status"] == "review_required":
            return {
                "status": "review_required",
                "stage": "ingest",
                "master_audio": None,
                "ingest_report": str(ingest_path),
                "review_reasons": ingest_result.get("review_reasons", []),
            }
        master_raw = ingest_result.get("master_audio")
        if not master_raw:
            raise RuntimeError("Ingest terminó sin master audio ni estado de revisión.")
        master_path = Path(master_raw)
        master_probe = probe_media(master_path)
        ingest_report = _load_ingest_report(ingest_path)
        _validate_master_timeline(source_path, source_probe, master_path, master_probe)
        _validate_ingest_provenance(source_path, master_path, ingest_report)

    transcript = transcribe_audio(
        master_path,
        model_name=model_name,
        language=language,
        device=device,
        compute_type=compute_type,
    )
    speech = detect_speech(
        master_path,
        min_silence_ms=250,
        speech_pad_ms=100,
    )

    candidates = build_candidates(
        transcript,
        speech,
        duration=float(source_probe["duration_seconds"]),
        mode=mode,
    )
    _append_semantic_candidates(
        candidates,
        build_semantic_candidates(transcript, mode=mode),
    )
    correction_scopes = build_correction_scopes(transcript, candidates)
    filler_assessments = build_filler_assessments(transcript, candidates)
    join_assessments = build_join_assessments(
        transcript,
        candidates,
        correction_scopes=correction_scopes,
        filler_assessments=filler_assessments,
    )
    semantic_decisions = build_semantic_decisions(transcript, candidates)

    stem = source_path.stem
    transcript_json = write_transcript_json(transcript, output_root / f"{stem}_transcript.json")
    transcript_txt = write_transcript_txt(transcript, output_root / f"{stem}_transcript.txt")
    subtitles = write_srt(transcript, output_root / f"{stem}.srt")
    report = build_analysis_report(
        source_path,
        source_probe,
        transcript,
        speech,
        mode=mode,
        candidates=candidates,
        master_audio=master_path,
        master_probe=master_probe,
        ingest_report=ingest_report,
        ingest_report_path=ingest_path,
    )
    attach_semantic_decisions(report, semantic_decisions)
    attach_correction_scopes(report, correction_scopes)
    attach_filler_assessments(report, filler_assessments)
    attach_join_assessments(report, join_assessments)
    analysis_path = save_analysis_report(report, output_root / f"{stem}_analysis.json")

    return {
        "status": "analyzed",
        "master_audio": str(master_path),
        "ingest_report": str(ingest_path),
        "analysis": str(analysis_path),
        "transcript_json": str(transcript_json),
        "transcript_txt": str(transcript_txt),
        "subtitles_srt": str(subtitles),
        "summary": report["summary"],
    }
