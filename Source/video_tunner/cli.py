from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from pathlib import Path

from . import __version__
from .analysis_pipeline import analyze_spoken_video
from .approval import (
    build_approval_record,
    load_json_object,
    save_approval_record,
    sha256_path,
    validate_approval_record,
)
from .edit_plan import MODE_SETTINGS, build_silence_plan, load_plan, save_plan
from .ingest import ingest_video
from .media import probe_media
from .render import render_from_plan
from .silence import detect_silences
from .sync import SyncDependencyError, SyncInsufficientSignalError
from .tools import (
    ToolNotFoundError,
    ensure_runtime_layout,
    model_root,
    portable_strict_mode,
    runtime_root,
    tool_version,
)
from .transcription import (
    TranscriptionDependencyError,
    WhisperModelNotFoundError,
    download_whisper_model,
    whisper_model_status,
)
from .vad import VadDependencyError


def _json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def _module_runtime_status(module: str) -> dict[str, str]:
    if importlib.util.find_spec(module) is None:
        return {"status": "missing"}
    try:
        loaded = importlib.import_module(module)
    except Exception as exc:
        return {"status": "error", "detail": f"{type(exc).__name__}: {exc}"}
    version = getattr(loaded, "__version__", None)
    return {"status": "available", **({"version": str(version)} if version else {})}


def _silero_asset_status() -> dict[str, str | bool]:
    if importlib.util.find_spec("faster_whisper") is None:
        return {"available": False, "detail": "faster_whisper missing"}
    try:
        from faster_whisper.utils import get_assets_path

        path = Path(get_assets_path()) / "silero_vad_v6.onnx"
        return {"available": path.is_file(), "path": str(path)}
    except Exception as exc:
        return {"available": False, "detail": f"{type(exc).__name__}: {exc}"}


def cmd_doctor(_: argparse.Namespace) -> int:
    layout = ensure_runtime_layout()
    report = {
        "video_tunner": __version__,
        "portable_mode": portable_strict_mode(),
        "runtime_root": str(runtime_root()),
        "runtime_layout": {key: str(value) for key, value in layout.items() if key != "root"},
        "model_root": str(model_root()),
        "analysis_dependencies": {
            "faster_whisper": _module_runtime_status("faster_whisper"),
            "ctranslate2": _module_runtime_status("ctranslate2"),
            "onnxruntime": _module_runtime_status("onnxruntime"),
            "tokenizers": _module_runtime_status("tokenizers"),
            "numpy": _module_runtime_status("numpy"),
            "av": _module_runtime_status("av"),
            "silero_onnx": _silero_asset_status(),
            "vad_backend": "faster-whisper Silero ONNX",
            "sync_backend": "Video_Tunner multi-anchor log-RMS correlation",
        },
    }
    for tool in ("ffmpeg", "ffprobe"):
        try:
            report[tool] = tool_version(tool)
        except ToolNotFoundError as exc:
            report[tool] = f"ERROR: {exc}"
    _json(report)
    return 0 if not any(str(value).startswith("ERROR:") for value in report.values()) else 2


def cmd_probe(args: argparse.Namespace) -> int:
    _json(probe_media(args.input))
    return 0


def cmd_model_status(args: argparse.Namespace) -> int:
    _json(whisper_model_status(args.model))
    return 0


def cmd_model_fetch(args: argparse.Namespace) -> int:
    path = download_whisper_model(args.model, replace=args.replace)
    _json(whisper_model_status(args.model) | {"downloaded_to": str(path)})
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    result = ingest_video(
        args.input,
        args.output_dir,
        external_audio=args.audio,
        manual_offset_seconds=args.offset,
        manual_drift_ppm=args.drift_ppm,
    )
    _json(result)
    return 0


def _analyse_silence(args: argparse.Namespace) -> tuple[dict, dict]:
    probe = probe_media(args.input)
    if probe["audio_streams"] < 1:
        raise ValueError("El vídeo no contiene una pista de audio analizable.")
    settings = MODE_SETTINGS[args.mode]
    silences = detect_silences(
        args.input,
        media_duration=float(probe["duration_seconds"]),
        noise_db=float(settings["noise_db"]),
        min_duration=float(settings["min_silence"]),
    )
    plan = build_silence_plan(args.input, probe, silences, mode=args.mode)
    return probe, plan


def cmd_plan(args: argparse.Namespace) -> int:
    _, plan = _analyse_silence(args)
    destination = save_plan(plan, args.output)
    print(destination)
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    result = analyze_spoken_video(
        args.input,
        args.output_dir,
        mode=args.mode,
        model_name=args.model,
        language=None if args.language == "auto" else args.language,
        device=args.device,
        compute_type=args.compute_type,
        external_audio=args.audio,
        manual_offset_seconds=args.offset,
        manual_drift_ppm=args.drift_ppm,
        master_audio=args.master_audio,
        ingest_report_path=args.ingest_report,
    )
    _json(result)
    return 0


def cmd_approval_create(args: argparse.Namespace) -> int:
    analysis = load_json_object(args.analysis)
    analysis_sha = sha256_path(args.analysis)
    record = build_approval_record(
        analysis,
        args.promotion_assessment,
        decision=args.decision,
        actor=args.actor,
        reason=args.reason,
        analysis_sha256=analysis_sha,
    )
    destination = save_approval_record(record, args.output)
    _json({"approval": str(destination), "record": record})
    return 0


def cmd_approval_validate(args: argparse.Namespace) -> int:
    analysis = load_json_object(args.analysis)
    approval = load_json_object(args.approval)
    validation = validate_approval_record(
        analysis,
        approval,
        analysis_sha256=sha256_path(args.analysis),
    )
    _json(validation)
    return 0 if validation.get("valid") else 3


def cmd_render(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    destination = render_from_plan(args.input, plan, args.output)
    print(destination)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    source = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _, plan = _analyse_silence(args)
    plan_path = save_plan(plan, output_dir / f"{source.stem}_edit_plan.json")
    video_path = render_from_plan(source, plan, output_dir / f"{source.stem}_clean.mp4")
    _json({"video": str(video_path), "edit_plan": str(plan_path), "summary": plan["summary"]})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-tunner")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Comprueba runtime portable, FFmpeg/ffprobe y stack de análisis.")
    doctor.set_defaults(func=cmd_doctor)

    probe = sub.add_parser("probe", help="Inspecciona un archivo audiovisual con ffprobe.")
    probe.add_argument("input")
    probe.set_defaults(func=cmd_probe)

    model = sub.add_parser("model", help="Gestiona modelos Whisper dentro del árbol local de Video_Tunner.")
    model_sub = model.add_subparsers(dest="model_command", required=True)

    model_status = model_sub.add_parser("status", help="Comprueba si un modelo Whisper local está completo.")
    model_status.add_argument("model")
    model_status.set_defaults(func=cmd_model_status)

    model_fetch = model_sub.add_parser("fetch", help="Descarga un modelo Whisper dentro de Models/whisper.")
    model_fetch.add_argument("model")
    model_fetch.add_argument("--replace", action="store_true")
    model_fetch.set_defaults(func=cmd_model_fetch)

    ingest = sub.add_parser(
        "ingest",
        help="Resuelve vídeo + audio opcional a un master audio sincronizado y auditable.",
    )
    ingest.add_argument("input", help="Vídeo principal.")
    ingest.add_argument("--audio", help="Audio externo opcional; si se omite usa audio embebido.")
    ingest.add_argument(
        "--offset",
        type=float,
        help=(
            "Override manual en segundos. Positivo = el audio externo empieza después del vídeo; "
            "negativo = antes."
        ),
    )
    ingest.add_argument(
        "--drift-ppm",
        type=float,
        default=0.0,
        help="Drift manual en ppm; requiere --offset. Default 0.",
    )
    ingest.add_argument("--output-dir", default="Output")
    ingest.set_defaults(func=cmd_ingest)

    plan = sub.add_parser("plan", help="Detecta silencios con FFmpeg y genera un Edit Plan JSON.")
    plan.add_argument("input")
    plan.add_argument("--mode", choices=MODE_SETTINGS, default="conservative")
    plan.add_argument("--output", default="edit_plan.json")
    plan.set_defaults(func=cmd_plan)

    analyze = sub.add_parser(
        "analyze",
        help="Resuelve master audio, transcribe, ejecuta VAD y genera candidatos sin aplicar cortes.",
    )
    analyze.add_argument("input", help="Vídeo principal cuya timeline gobierna todos los timestamps.")
    analyze.add_argument("--audio", help="Audio externo opcional; analyze ejecutará ingest/sync antes de Whisper/VAD.")
    analyze.add_argument(
        "--offset",
        type=float,
        help="Override manual de sync para --audio, con la misma convención que `ingest`.",
    )
    analyze.add_argument(
        "--drift-ppm",
        type=float,
        default=0.0,
        help="Drift manual para --audio; requiere --offset.",
    )
    analyze.add_argument(
        "--master-audio",
        help="Master ya materializado. Requiere --ingest-report y no puede combinarse con --audio/--offset.",
    )
    analyze.add_argument(
        "--ingest-report",
        help="ingest.json que acredita la procedencia de --master-audio.",
    )
    analyze.add_argument("--mode", choices=MODE_SETTINGS, default="conservative")
    analyze.add_argument("--output-dir", default="Output")
    analyze.add_argument("--model", default="large-v3-turbo")
    analyze.add_argument("--language", default="auto", help="Idioma Whisper (p. ej. es) o auto.")
    analyze.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cpu")
    analyze.add_argument("--compute-type", default="auto")
    analyze.set_defaults(func=cmd_analyze)

    approval = sub.add_parser(
        "approval",
        help="Crea o valida decisiones explícitas sobre promotion assessments sin generar edits.",
    )
    approval_sub = approval.add_subparsers(dest="approval_command", required=True)

    approval_create = approval_sub.add_parser(
        "create",
        help="Crea un artefacto auditable APPROVE/REJECT ligado al analysis.json exacto.",
    )
    approval_create.add_argument("analysis", help="analysis.json schema v9+ que contiene la promotion assessment.")
    approval_create.add_argument("--promotion-assessment", required=True, help="ID exacto de promotion assessment.")
    approval_create.add_argument("--decision", required=True, choices=("approve", "reject"))
    approval_create.add_argument("--actor", required=True, help="Identidad/etiqueta del revisor humano.")
    approval_create.add_argument("--reason", required=True, help="Motivo auditable de la decisión.")
    approval_create.add_argument("--output", default="promotion_approval.json")
    approval_create.set_defaults(func=cmd_approval_create)

    approval_validate = approval_sub.add_parser(
        "validate",
        help="Valida fingerprint, provenance y vigencia de un artefacto de aprobación.",
    )
    approval_validate.add_argument("analysis", help="analysis.json actual contra el que validar.")
    approval_validate.add_argument("approval", help="promotion_approval.json a validar.")
    approval_validate.set_defaults(func=cmd_approval_validate)

    render = sub.add_parser("render", help="Renderiza un vídeo a partir de un Edit Plan.")
    render.add_argument("input")
    render.add_argument("plan")
    render.add_argument("output")
    render.set_defaults(func=cmd_render)

    clean = sub.add_parser("clean", help="Cleaner actual: elimina silencios FFmpeg de forma auditable.")
    clean.add_argument("input")
    clean.add_argument("--mode", choices=MODE_SETTINGS, default="conservative")
    clean.add_argument("--output-dir", default="Output")
    clean.set_defaults(func=cmd_clean)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (
        FileNotFoundError,
        ToolNotFoundError,
        SyncDependencyError,
        SyncInsufficientSignalError,
        TranscriptionDependencyError,
        WhisperModelNotFoundError,
        VadDependencyError,
        ValueError,
        RuntimeError,
    ) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
