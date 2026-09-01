from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .silence import SilenceInterval, silence_removals

MODE_SETTINGS = {
    "conservative": {"noise_db": -40.0, "min_silence": 0.65, "keep_pause": 0.20},
    "aggressive": {"noise_db": -38.0, "min_silence": 0.35, "keep_pause": 0.10},
}


def build_silence_plan(
    source: str | Path,
    probe: dict[str, Any],
    silences: list[SilenceInterval],
    *,
    mode: str,
) -> dict[str, Any]:
    if mode not in MODE_SETTINGS:
        raise ValueError(f"Modo desconocido: {mode}")

    settings = MODE_SETTINGS[mode]
    cuts = silence_removals(silences, keep_pause=float(settings["keep_pause"]))
    removed = sum(float(cut["duration"]) for cut in cuts)

    return {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "file": Path(source).name,
            "duration_seconds": probe["duration_seconds"],
        },
        "mode": mode,
        "analysis": {
            "silence": settings,
        },
        "edits": cuts,
        "summary": {
            "edit_count": len(cuts),
            "removed_seconds": round(removed, 6),
            "estimated_output_seconds": round(max(0.0, probe["duration_seconds"] - removed), 6),
        },
    }


def save_plan(plan: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_plan(source: str | Path) -> dict[str, Any]:
    return json.loads(Path(source).read_text(encoding="utf-8"))
