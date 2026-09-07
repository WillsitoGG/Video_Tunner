from __future__ import annotations

import hashlib
import io
import json
import shutil
import sys
import urllib.error
import urllib.request
import wave
import zipfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
DOWNLOAD_ROOT = REPO_ROOT / ".phase3_denoise_corpus_download"

MIRROR_PREFIX = "https://huggingface.co/datasets/mrfakename/noisy-speech-files/resolve/main/"


def md5_path(path: Path) -> str:
    digest = hashlib.md5()  # nosec B324 - integrity against publisher-provided checksum, not security use
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Video_Tunner corpus validator"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)


def download_verified_archive(archive: dict[str, Any]) -> tuple[Path, str]:
    destination = DOWNLOAD_ROOT / str(archive["filename"])
    expected_md5 = str(archive["md5"]).lower()
    urls = [
        str(archive["legacy_download_url"]),
        MIRROR_PREFIX + str(archive["filename"]) + "?download=true",
    ]
    errors: list[str] = []
    for index, url in enumerate(urls):
        try:
            if destination.exists():
                destination.unlink()
            print(f"PHASE3_DENOISE_CORPUS_DOWNLOAD_ATTEMPT={archive['filename']} source={index + 1}")
            _download(url, destination)
            actual_md5 = md5_path(destination)
            if actual_md5 != expected_md5:
                errors.append(f"{url}: md5 {actual_md5} != {expected_md5}")
                destination.unlink(missing_ok=True)
                continue
            transport = "edinburgh_legacy" if index == 0 else "verified_mirror"
            print(f"PHASE3_DENOISE_CORPUS_ARCHIVE={archive['filename']} MD5_OK=1 TRANSPORT={transport}")
            return destination, transport
        except (OSError, urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"{url}: {type(exc).__name__}: {exc}")
            destination.unlink(missing_ok=True)
    raise RuntimeError(
        f"No se pudo materializar {archive['filename']} con el MD5 oficial. "
        + " | ".join(errors)
    )


def zip_basename_map(archive_path: Path) -> dict[str, str]:
    with zipfile.ZipFile(archive_path) as archive:
        names: dict[str, str] = {}
        for member in archive.namelist():
            if member.endswith("/"):
                continue
            basename = Path(member).name
            if basename in names:
                raise ValueError(f"Basename duplicado en {archive_path.name}: {basename}")
            names[basename] = member
        return names


def read_zip_member(archive_path: Path, member: str) -> bytes:
    with zipfile.ZipFile(archive_path) as archive:
        return archive.read(member)


def wav_contract(data: bytes) -> dict[str, Any]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        return {
            "channels": int(wav.getnchannels()),
            "sample_width_bytes": int(wav.getsampwidth()),
            "sample_rate_hz": int(wav.getframerate()),
            "frame_count": int(wav.getnframes()),
            "duration_seconds": wav.getnframes() / float(wav.getframerate()),
        }


def parse_log_testset(log_text: str) -> dict[str, tuple[str, float]]:
    records: dict[str, tuple[str, float]] = {}
    for raw in log_text.splitlines():
        parts = raw.strip().split()
        if len(parts) != 3:
            continue
        case_id, noise, snr_raw = parts
        try:
            snr = float(snr_raw)
        except ValueError:
            continue
        if case_id in records:
            raise ValueError(f"Case duplicado en log_testset: {case_id}")
        records[case_id] = (noise, snr)
    if not records:
        raise ValueError("log_testset.txt no produjo registros.")
    return records


def find_log_testset(log_archive: Path) -> str:
    with zipfile.ZipFile(log_archive) as archive:
        candidates = [name for name in archive.namelist() if Path(name).name == "log_testset.txt"]
        if len(candidates) != 1:
            raise ValueError(f"Se esperaba exactamente un log_testset.txt; encontrados {len(candidates)}")
        return archive.read(candidates[0]).decode("utf-8")


def main() -> int:
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

    clean_path, clean_transport = download_verified_archive(payload["archives"]["clean_testset"])
    noisy_path, noisy_transport = download_verified_archive(payload["archives"]["noisy_testset"])
    log_path, log_transport = download_verified_archive(payload["archives"]["logfiles"])

    clean_members = zip_basename_map(clean_path)
    noisy_members = zip_basename_map(noisy_path)
    log_records = parse_log_testset(find_log_testset(log_path))

    expected_sample_rate = int(payload["dataset"]["native_sample_rate_hz"])
    materialized: list[dict[str, Any]] = []
    for case in payload["cases"]:
        case_id = str(case["id"])
        basename = case_id + ".wav"
        if basename not in clean_members:
            raise FileNotFoundError(f"Clean pair missing: {basename}")
        if basename not in noisy_members:
            raise FileNotFoundError(f"Noisy pair missing: {basename}")
        if case_id not in log_records:
            raise FileNotFoundError(f"Condition log missing: {case_id}")

        logged_noise, logged_snr = log_records[case_id]
        if logged_noise != case["noise"] or abs(logged_snr - float(case["snr_db"])) > 1e-9:
            raise ValueError(
                f"Condition mismatch {case_id}: log=({logged_noise},{logged_snr}) "
                f"fixture=({case['noise']},{case['snr_db']})"
            )

        clean_data = read_zip_member(clean_path, clean_members[basename])
        noisy_data = read_zip_member(noisy_path, noisy_members[basename])
        clean_wav = wav_contract(clean_data)
        noisy_wav = wav_contract(noisy_data)
        for label, contract in (("clean", clean_wav), ("noisy", noisy_wav)):
            if contract["sample_rate_hz"] != expected_sample_rate:
                raise ValueError(f"{case_id} {label}: sample rate inesperado {contract['sample_rate_hz']}")
            if contract["channels"] != 1:
                raise ValueError(f"{case_id} {label}: se esperaba mono")
            if contract["sample_width_bytes"] != 2:
                raise ValueError(f"{case_id} {label}: se esperaba PCM16")
        if clean_wav["frame_count"] != noisy_wav["frame_count"]:
            raise ValueError(
                f"{case_id}: clean/noisy frame count difiere "
                f"{clean_wav['frame_count']} != {noisy_wav['frame_count']}"
            )

        materialized.append(
            {
                "id": case_id,
                "speaker": case["speaker"],
                "noise": case["noise"],
                "snr_db": float(case["snr_db"]),
                "clean_sha256": sha256_bytes(clean_data),
                "noisy_sha256": sha256_bytes(noisy_data),
                "sample_rate_hz": clean_wav["sample_rate_hz"],
                "frame_count": clean_wav["frame_count"],
                "duration_seconds": round(clean_wav["duration_seconds"], 6),
            }
        )

    if len(materialized) != int(payload["selection_policy"]["required_cases"]):
        raise ValueError("Materialized case count no coincide con fixture.")

    manifest = {
        "schema_version": 1,
        "record_type": "denoise_evaluation_corpus_materialization",
        "corpus_id": payload["corpus_id"],
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "dataset_doi": payload["dataset"]["persistent_identifier"],
        "license": payload["dataset"]["license"],
        "archive_md5": {
            key: payload["archives"][key]["md5"]
            for key in ("clean_testset", "noisy_testset", "logfiles")
        },
        "transport": {
            "clean_testset": clean_transport,
            "noisy_testset": noisy_transport,
            "logfiles": log_transport,
            "note": "Any mirror transport is accepted only after exact match to the publisher-provided archive MD5.",
        },
        "case_count": len(materialized),
        "cases": materialized,
        "evaluation_policy": payload["evaluation_policy"],
    }
    destination = REPO_ROOT / "phase3-denoise-corpus-materialization.json"
    destination.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"PHASE3_DENOISE_CORPUS_CASES={len(materialized)}")
    print(f"PHASE3_DENOISE_CORPUS_SPEAKERS={len({item['speaker'] for item in materialized})}")
    print(f"PHASE3_DENOISE_CORPUS_NOISE_TYPES={len({item['noise'] for item in materialized})}")
    print(f"PHASE3_DENOISE_CORPUS_SNR_LEVELS={len({item['snr_db'] for item in materialized})}")
    print("PHASE3_DENOISE_CORPUS_MATERIALIZATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
