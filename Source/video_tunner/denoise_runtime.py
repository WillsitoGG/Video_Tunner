from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from .tools import runtime_root


SELECTED_DENOISER_ID = "deepfilternet_0_5_6_compensated_v1"
DEEPFILTER_VERSION = "0.5.6"
DEEPFILTER_ASSET_NAME = "deep-filter-0.5.6-x86_64-pc-windows-msvc.exe"
DEEPFILTER_ASSET_URL = (
    "https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/"
    "deep-filter-0.5.6-x86_64-pc-windows-msvc.exe"
)
DEEPFILTER_ASSET_SHA256 = "75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915"
DEEPFILTER_ASSET_SIZE_BYTES = 26912256
DEEPFILTER_RUNTIME_RELATIVE_PATH = Path("Tools") / "deepfilter" / "bin" / "deep-filter.exe"
DEEPFILTER_ARGUMENTS = ["--compensate-delay", "--output-dir", "<output_dir>", "<input_wav>"]
DEEPFILTER_INPUT_PCM = "pcm_s16le"
DEEPFILTER_INPUT_CHANNELS = 1
DEEPFILTER_INPUT_SAMPLE_RATE_HZ = 48000
DEEPFILTER_OUTPUT_CHANNELS = 1
DEEPFILTER_OUTPUT_SAMPLE_RATE_HZ = 48000
DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS = 0.05


class DenoiserRuntimeError(RuntimeError):
    pass


def selected_denoiser_contract() -> dict[str, Any]:
    return {
        "candidate_id": SELECTED_DENOISER_ID,
        "implementation": "deep-filter",
        "version": DEEPFILTER_VERSION,
        "asset_name": DEEPFILTER_ASSET_NAME,
        "asset_url": DEEPFILTER_ASSET_URL,
        "asset_sha256": DEEPFILTER_ASSET_SHA256,
        "asset_size_bytes": DEEPFILTER_ASSET_SIZE_BYTES,
        "runtime_relative_path": DEEPFILTER_RUNTIME_RELATIVE_PATH.as_posix(),
        "arguments": list(DEEPFILTER_ARGUMENTS),
        "explicit_model_argument": False,
        "media_contract": {
            "input_pcm": DEEPFILTER_INPUT_PCM,
            "input_channels": DEEPFILTER_INPUT_CHANNELS,
            "input_sample_rate_hz": DEEPFILTER_INPUT_SAMPLE_RATE_HZ,
            "output_channels": DEEPFILTER_OUTPUT_CHANNELS,
            "output_sample_rate_hz": DEEPFILTER_OUTPUT_SAMPLE_RATE_HZ,
            "raw_duration_delta_max_seconds": DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
        },
        "integration_state": {
            "selected_for_integration_review_only": True,
            "runtime_download_allowed": False,
            "product_default": "preserve",
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }


def deepfilter_executable_path(root: Path | None = None) -> Path:
    base = Path(root).resolve() if root is not None else runtime_root()
    return base / DEEPFILTER_RUNTIME_RELATIVE_PATH


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_probe(executable: Path, argument: str) -> str:
    completed = subprocess.run(
        [str(executable), argument],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise DenoiserRuntimeError(
            f"DeepFilterNet probe {argument} falló con código {completed.returncode}."
        )
    return ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()


def validate_selected_denoiser_binary(
    path: Path | None = None,
    *,
    probe_cli: bool = False,
) -> dict[str, Any]:
    executable = Path(path).resolve() if path is not None else deepfilter_executable_path()
    if not executable.is_file():
        raise DenoiserRuntimeError(
            f"No se encontró el DeepFilterNet seleccionado dentro del runtime portable: {executable}. "
            "No se permite descargarlo ni resolverlo desde PATH en runtime."
        )

    actual_size = executable.stat().st_size
    if actual_size != DEEPFILTER_ASSET_SIZE_BYTES:
        raise DenoiserRuntimeError(
            f"DeepFilterNet size mismatch: esperado {DEEPFILTER_ASSET_SIZE_BYTES}, obtenido {actual_size}."
        )

    actual_sha = sha256_path(executable)
    if actual_sha != DEEPFILTER_ASSET_SHA256:
        raise DenoiserRuntimeError(
            f"DeepFilterNet SHA256 mismatch: esperado {DEEPFILTER_ASSET_SHA256}, obtenido {actual_sha}."
        )

    result: dict[str, Any] = {
        "valid": True,
        "path": str(executable),
        "candidate_id": SELECTED_DENOISER_ID,
        "version": DEEPFILTER_VERSION,
        "asset_sha256": actual_sha,
        "asset_size_bytes": actual_size,
        "runtime_download_allowed": False,
        "denoise_authorized": False,
        "renderer_authorized": False,
        "auto_apply": False,
    }

    if probe_cli:
        version_text = _run_probe(executable, "--version")
        if DEEPFILTER_VERSION not in version_text:
            raise DenoiserRuntimeError("DeepFilterNet version output no cumple el contrato 0.5.6.")
        help_text = _run_probe(executable, "--help")
        for token in ("--compensate-delay", "--output-dir"):
            if token not in help_text:
                raise DenoiserRuntimeError(f"DeepFilterNet CLI contract no contiene {token}.")
        result["version_output"] = version_text
        result["cli_contract_pass"] = True

    return result
