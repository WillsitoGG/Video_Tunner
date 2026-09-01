from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


class ToolNotFoundError(RuntimeError):
    pass


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _tool_filename(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def tool_candidates(name: str) -> list[Path]:
    filename = _tool_filename(name)
    candidates: list[Path] = []

    env_dir = os.getenv("VIDEO_TUNNER_FFMPEG_DIR")
    if env_dir:
        candidates.append(Path(env_dir) / filename)

    candidates.append(runtime_root() / "Tools" / "ffmpeg" / "bin" / filename)

    discovered = shutil.which(name)
    if discovered:
        candidates.append(Path(discovered))

    return candidates


def resolve_tool(name: str) -> Path:
    for candidate in tool_candidates(name):
        if candidate.is_file():
            return candidate.resolve()
    raise ToolNotFoundError(
        f"No se encontró {name}. Define VIDEO_TUNNER_FFMPEG_DIR, "
        "inclúyelo en Tools/ffmpeg/bin o añádelo temporalmente al PATH."
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
