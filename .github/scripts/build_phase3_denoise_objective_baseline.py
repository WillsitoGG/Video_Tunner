from __future__ import annotations

import hashlib
import io
import json
import math
import statistics
import wave
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from video_tunner.denoise_objective import compute_paired_objective_metrics


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
POLICY = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_objective_metric_policy_v1.json"
MATERIALIZATION = REPO_ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
DOWNLOAD_ROOT = REPO_ROOT / ".phase3_denoise_corpus_download"
OUTPUT = REPO_ROOT / "phase3-denoise-objective-baseline.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def read_member(archive_path: Path, member: str) -> bytes:
    with zipfile.ZipFile(archive_path) as archive:
        return archive.read(member)


def pcm16_mono(data: bytes) -> tuple[np.ndarray, int, int]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("3.6c requiere WAV PCM16 mono.")
        sample_rate = int(wav.getframerate())
        frames = int(wav.getnframes())
        raw = wav.readframes(frames)
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if samples.size != frames:
        raise ValueError("Frame count PCM decodificado no coincide con cabecera WAV.")
    return samples, sample_rate, frames


def aggregate(values: list[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError("No se pueden agregar métricas vacías/no finitas.")
    return {
        "mean": round(statistics.fmean(values), 8),
        "median": round(statistics.median(values), 8),
        "min": round(min(values), 8),
        "max": round(max(values), 8),
    }


def grouped(cases: list[dict[str, Any]], field: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    keys = sorted({case[field] for case in cases}, key=lambda value: str(value))
    for key in keys:
        selected = [case for case in cases if case[field] == key]
        result[str(key)] = {
            "case_count": len(selected),
            "si_sdr_db": {
                "mean": round(statistics.fmean(case["metrics"]["si_sdr_db"] for case in selected), 8),
                "median": round(statistics.median(case["metrics"]["si_sdr_db"] for case in selected), 8),
            },
            "stoi": {
                "mean": round(statistics.fmean(case["metrics"]["stoi"] for case in selected), 8),
                "median": round(statistics.median(case["metrics"]["stoi"] for case in selected), 8),
            },
        }
    return result


def main() -> int:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    materialization = json.loads(MATERIALIZATION.read_text(encoding="utf-8"))

    fixture_sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    policy_sha = hashlib.sha256(POLICY.read_bytes()).hexdigest()
    materialization_sha = hashlib.sha256(MATERIALIZATION.read_bytes()).hexdigest()
    if policy["corpus_fixture_sha256"] != fixture_sha:
        raise ValueError("Metric policy no está ligada al corpus fixture actual.")
    if materialization["fixture_sha256"] != fixture_sha:
        raise ValueError("Materialization evidence no está ligada al corpus fixture actual.")
    if fixture["corpus_id"] != materialization["corpus_id"] or fixture["corpus_id"] != policy["corpus_id"]:
        raise ValueError("Corpus id mismatch entre fixture/policy/materialization.")

    clean_zip = DOWNLOAD_ROOT / fixture["archives"]["clean_testset"]["filename"]
    noisy_zip = DOWNLOAD_ROOT / fixture["archives"]["noisy_testset"]["filename"]
    if not clean_zip.is_file() or not noisy_zip.is_file():
        raise FileNotFoundError("Ejecuta primero validate_phase3_denoise_corpus.py para materializar ZIPs verificados.")
    clean_members = zip_basename_map(clean_zip)
    noisy_members = zip_basename_map(noisy_zip)

    evidence_by_id = {case["id"]: case for case in materialization["cases"]}
    cases: list[dict[str, Any]] = []
    for frozen in fixture["cases"]:
        case_id = frozen["id"]
        basename = case_id + ".wav"
        clean_data = read_member(clean_zip, clean_members[basename])
        noisy_data = read_member(noisy_zip, noisy_members[basename])
        evidence = evidence_by_id[case_id]
        if sha256_bytes(clean_data) != evidence["clean_sha256"]:
            raise ValueError(f"{case_id}: clean SHA no coincide con materialization evidence.")
        if sha256_bytes(noisy_data) != evidence["noisy_sha256"]:
            raise ValueError(f"{case_id}: noisy SHA no coincide con materialization evidence.")

        clean, clean_rate, clean_frames = pcm16_mono(clean_data)
        noisy, noisy_rate, noisy_frames = pcm16_mono(noisy_data)
        if clean_rate != noisy_rate or clean_frames != noisy_frames:
            raise ValueError(f"{case_id}: clean/noisy alignment contract roto.")
        if clean_rate != int(policy["input_contract"]["native_sample_rate_hz"]):
            raise ValueError(f"{case_id}: sample rate inesperado para policy.")

        metrics = compute_paired_objective_metrics(
            clean,
            noisy,
            sample_rate_hz=clean_rate,
        )
        cases.append(
            {
                "id": case_id,
                "speaker": frozen["speaker"],
                "noise": frozen["noise"],
                "snr_db": float(frozen["snr_db"]),
                "clean_sha256": evidence["clean_sha256"],
                "noisy_sha256": evidence["noisy_sha256"],
                "frame_count": clean_frames,
                "sample_rate_hz": clean_rate,
                "metrics": metrics,
            }
        )

    required_cases = int(policy["baseline_policy"]["required_cases"])
    if len(cases) != required_cases:
        raise ValueError(f"Baseline incompleta: {len(cases)} != {required_cases}")

    si_values = [case["metrics"]["si_sdr_db"] for case in cases]
    stoi_values = [case["metrics"]["stoi"] for case in cases]
    baseline = {
        "schema_version": 1,
        "record_type": "denoise_objective_baseline",
        "status": "baseline_measurement_complete",
        "valid": True,
        "corpus_id": fixture["corpus_id"],
        "bindings": {
            "corpus_fixture_sha256": fixture_sha,
            "metric_policy_sha256": policy_sha,
            "materialization_evidence_sha256": materialization_sha,
            "raw_materialization_manifest_sha256": materialization["provenance"]["raw_manifest_sha256"],
        },
        "metric_policy_id": policy["policy_id"],
        "case_count": len(cases),
        "cases": cases,
        "summary": {
            "overall": {
                "si_sdr_db": aggregate(si_values),
                "stoi": aggregate(stoi_values),
            },
            "by_speaker": grouped(cases, "speaker"),
            "by_noise": grouped(cases, "noise"),
            "by_snr_db": grouped(cases, "snr_db"),
        },
        "interpretation": {
            "descriptive_noisy_baseline_only": True,
            "objective_metrics_are_auxiliary_only": True,
            "acceptance_thresholds_defined": False,
            "algorithm_ranking_authorized": False,
            "denoiser_selected": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "human_perceptual_comparison_required_before_treatment_authorization": True,
            "auto_apply": False,
        },
    }
    OUTPUT.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"PHASE3_DENOISE_BASELINE_CASES={len(cases)}")
    print(f"PHASE3_DENOISE_BASELINE_SISDR_MEAN={baseline['summary']['overall']['si_sdr_db']['mean']}")
    print(f"PHASE3_DENOISE_BASELINE_STOI_MEAN={baseline['summary']['overall']['stoi']['mean']}")
    print("PHASE3_DENOISE_OBJECTIVE_BASELINE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
