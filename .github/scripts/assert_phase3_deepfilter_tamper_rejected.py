from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from video_tunner.denoise_runtime import DenoiserRuntimeError, validate_selected_denoiser_binary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--tampered", required=True)
    args = parser.parse_args()

    source = Path(args.source).resolve()
    tampered = Path(args.tampered).resolve()
    tampered.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, tampered)
    with tampered.open("ab") as handle:
        handle.write(b"\x00")

    try:
        validate_selected_denoiser_binary(tampered)
    except DenoiserRuntimeError as exc:
        print(f"PHASE3_6G_TAMPER_FAIL_CLOSED=PASS {exc}")
        return 0

    print("PHASE3_6G_TAMPER_FAIL_CLOSED=FAIL tampered binary was accepted")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
