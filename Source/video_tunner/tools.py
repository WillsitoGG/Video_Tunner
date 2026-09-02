from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class ToolNotFoundError(RuntimeError):
    pass


def is_frozen_runtime() -> bool:
    return bool(getattr(sys, "frozen", False))


def portable_strict_mode() -> bool:
    value = os.getenv("VIDEO_TUNNER_PORTABLE_STRICT", "").strip().lower()
    return is_frozen_runtime() or value in {"1", "true", "yes", "on"}


def runtime_root() -> Path:
    if is_frozen_runtime():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def runtime_layout() -> dict[str, Path]:
    root = runtime_root()
    return {
        "root": root,
        "models": root / "Models",
        "temp": root / "Temp",
        "cache": root / "Cache",
        "config": root / "Config",
        "logs": root / "Logs",
        "output": root / "Output",
        "ffmpeg_bin": root / "Tools" / "ffmpeg" / "bin",
    }


def ensure_runtime_layout() -> dict[str, Path]:
    layout = runtime_layout()
    for key in ("models", "temp", "cache", "config", "logs", "output"):
        layout[key].mkdir(parents=True, exist_ok=True)
    return layout


def model_root() -> Path:
    if portable_strict_mode():
        return runtime_layout()["models"]
    env_dir = os.getenv("VIDEO_TUNNER_MODEL_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return runtime_layout()["models"]


def _tool_filename(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def tool_candidates(name: str) -> list[Path]:
    filename = _tool_filename(name)
    bundled = runtime_layout()["ffmpeg_bin"] / filename

    if portable_strict_mode():
        return [bundled]

    candidates: list[Path] = []
    env_dir = os.getenv("VIDEO_TUNNER_FFMPEG_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / filename)

    candidates.append(bundled)

    discovered = shutil.which(name)
    if discovered:
        candidates.append(Path(discovered))

    return candidates


def resolve_tool(name: str) -> Path:
    for candidate in tool_candidates(name):
        if candidate.is_file():
            return candidate.resolve()

    if portable_strict_mode():
        expected = runtime_layout()["ffmpeg_bin"] / _tool_filename(name)
        raise ToolNotFoundError(
            f"No se encontró {name} dentro del runtime portable: {expected}. "
            "En modo portable no se usa PATH ni herramientas externas."
        )

    raise ToolNotFoundError(
        f"No se encontró {name}. Define VIDEO_TUNNER_FFMPEG_DIR, "
        "inclúyelo en Tools/ffmpeg/bin o añádelo temporalmente al PATH durante desarrollo."
    )


def tool_version(name: str) -> str:
    executable = resolve_tool(name)
    completed = subprocess.run(
        [str(executable), "-version"],
        capture_output=True,
        text=True,
        check=True,
    )
    first_line = (completed.stdout or completed.stderr).splitlines()[0]
    return first_line.strip()
