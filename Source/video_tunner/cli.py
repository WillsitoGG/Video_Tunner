from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .edit_plan import MODE_SETTINGS, build_silence_plan, load_plan, save_plan
from .media import probe_media
from .render import render_from_plan
from .silence import detect_silences
from .tools import ToolNotFoundError, runtime_root, tool_version


def _json(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_doctor(_: argparse.Namespace) -> int:
    report = {"video_tunner": __version__, "runtime_root": str(runtime_root())}
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


def _analyse(args: argparse.Namespace) -> tuple[dict, dict]:
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
    _, plan = _analyse(args)
    destination = save_plan(plan, args.output)
    print(destination)
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    plan = load_plan(args.plan)
    destination = render_from_plan(args.input, plan, args.output)
    print(destination)
    return 0


def cmd_clean(args: argparse.Namespace) -> int:
    source = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _, plan = _analyse(args)
    plan_path = save_plan(plan, output_dir / f"{source.stem}_edit_plan.json")
    video_path = render_from_plan(source, plan, output_dir / f"{source.stem}_clean.mp4")
    _json({"video": str(video_path), "edit_plan": str(plan_path), "summary": plan["summary"]})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-tunner")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Comprueba FFmpeg/ffprobe y el runtime.")
    doctor.set_defaults(func=cmd_doctor)

    probe = sub.add_parser("probe", help="Inspecciona un archivo audiovisual con ffprobe.")
    probe.add_argument("input")
    probe.set_defaults(func=cmd_probe)

    plan = sub.add_parser("plan", help="Detecta silencios y genera un Edit Plan JSON.")
    plan.add_argument("input")
    plan.add_argument("--mode", choices=MODE_SETTINGS, default="conservative")
    plan.add_argument("--output", default="edit_plan.json")
    plan.set_defaults(func=cmd_plan)

    render = sub.add_parser("render", help="Renderiza un vídeo a partir de un Edit Plan.")
    render.add_argument("input")
    render.add_argument("plan")
    render.add_argument("output")
    render.set_defaults(func=cmd_render)

    clean = sub.add_parser("clean", help="Primer Cleaner: elimina silencios de forma auditable.")
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
    except (FileNotFoundError, ToolNotFoundError, ValueError, RuntimeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
