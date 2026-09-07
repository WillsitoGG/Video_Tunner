from __future__ import annotations

import hashlib
import io
import json
import math
import shutil
import statistics
import subprocess
import tempfile
import urllib.request
import wave
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from video_tunner.denoise_objective import (
    compute_clean_preservation_metrics,
    compute_paired_objective_metrics,
    right_tail_normalize,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
METRIC_POLICY = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_objective_metric_policy_v1.json"
CANDIDATE_POLICY = REPO_ROOT / "tests" / "fixtures" / "phase3_denoiser_candidate_comparison_policy_v1.json"
MATERIALIZATION = REPO_ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
BASELINE = REPO_ROOT / "Validation" / "phase3-denoise-objective-baseline.json"
DOWNLOAD_ROOT = REPO_ROOT / ".phase3_denoise_corpus_download"
OUTPUT = REPO_ROOT / "phase3-denoiser-candidate-comparison.json"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def pcm16_mono_path(path: Path) -> tuple[np.ndarray, int, int]:
    with wave.open(str(path), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError(f"{path.name}: se requiere WAV PCM16 mono para métrica.")
        rate = int(wav.getframerate())
        frames = int(wav.getnframes())
        raw = wav.readframes(frames)
    samples = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if samples.size != frames:
        raise ValueError(f"{path.name}: frame count decodificado no coincide con cabecera.")
    return samples, rate, frames


def pcm16_mono_bytes(data: bytes, destination: Path) -> tuple[np.ndarray, int, int]:
    destination.write_bytes(data)
    return pcm16_mono_path(destination)


def run_checked(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"Command failed ({completed.returncode}): {' '.join(command)}\n"
            f"stdout={completed.stdout[-3000:]}\nstderr={completed.stderr[-3000:]}"
        )
    return (completed.stdout + "\n" + completed.stderr).strip()


def ffmpeg_version(ffmpeg: str) -> str:
    text = run_checked([ffmpeg, "-version"])
    first = text.splitlines()[0] if text.splitlines() else ""
    return first


def render_afftdn(*, ffmpeg: str, source: Path, destination: Path, filter_spec: str) -> None:
    run_checked(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-af",
            filter_spec,
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )


def acquire_deepfilter(candidate: dict[str, Any], destination: Path) -> dict[str, Any]:
    request = urllib.request.Request(
        str(candidate["asset_url"]),
        headers={"User-Agent": "Video_Tunner Phase 3 denoiser evaluator"},
    )
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    actual_sha = sha256_path(destination)
    actual_size = destination.stat().st_size
    if actual_sha != candidate["asset_sha256"]:
        raise ValueError("DeepFilterNet SHA256 no coincide con policy congelada.")
    if actual_size != int(candidate["asset_size_bytes"]):
        raise ValueError("DeepFilterNet size no coincide con policy congelada.")
    version = run_checked([str(destination), "--version"])
    if str(candidate["version"]) not in version:
        raise ValueError("DeepFilterNet version no coincide con policy congelada.")
    help_text = run_checked([str(destination), "--help"])
    if "--compensate-delay" not in help_text or "--output-dir" not in help_text:
        raise ValueError("DeepFilterNet CLI contract no coincide con policy congelada.")
    return {
        "version_output": version.strip(),
        "asset_sha256": actual_sha,
        "asset_size_bytes": actual_size,
    }


def render_deepfilter(*, executable: Path, source: Path, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_checked(
        [
            str(executable),
            "--compensate-delay",
            "--output-dir",
            str(output_dir),
            str(source),
        ]
    )
    outputs = sorted(output_dir.glob("*.wav"))
    if len(outputs) != 1:
        raise ValueError(f"DeepFilterNet produjo {len(outputs)} WAVs para {source.name}; se esperaba 1.")
    return outputs[0]


def decode_candidate_to_pcm16(*, ffmpeg: str, source: Path, destination: Path) -> tuple[np.ndarray, int, int]:
    run_checked(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ]
    )
    return pcm16_mono_path(destination)


def aggregate(values: list[float]) -> dict[str, float]:
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError("No se pueden agregar métricas vacías/no finitas.")
    return {
        "mean": round(statistics.fmean(values), 8),
        "median": round(statistics.median(values), 8),
        "min": round(min(values), 8),
        "max": round(max(values), 8),
    }


def grouped_noisy(cases: list[dict[str, Any]], field: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in sorted({case[field] for case in cases}, key=lambda value: str(value)):
        selected = [case for case in cases if case[field] == key]
        result[str(key)] = {
            "case_count": len(selected),
            "si_sdr_db": aggregate([case["metrics"]["si_sdr_db"] for case in selected]),
            "stoi": aggregate([case["metrics"]["stoi"] for case in selected]),
            "delta_vs_preserve": {
                "si_sdr_db": aggregate([case["delta_vs_preserve"]["si_sdr_db"] for case in selected]),
                "stoi": aggregate([case["delta_vs_preserve"]["stoi"] for case in selected]),
            },
        }
    return result


def summarize_noisy(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "overall": {
            "case_count": len(cases),
            "si_sdr_db": aggregate([case["metrics"]["si_sdr_db"] for case in cases]),
            "stoi": aggregate([case["metrics"]["stoi"] for case in cases]),
            "delta_vs_preserve": {
                "si_sdr_db": aggregate([case["delta_vs_preserve"]["si_sdr_db"] for case in cases]),
                "stoi": aggregate([case["delta_vs_preserve"]["stoi"] for case in cases]),
            },
        },
        "by_speaker": grouped_noisy(cases, "speaker"),
        "by_noise": grouped_noisy(cases, "noise"),
        "by_snr_db": grouped_noisy(cases, "snr_db"),
    }


def summarize_clean(cases: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "case_count": len(cases),
        "stoi": aggregate([case["metrics"]["stoi"] for case in cases]),
        "normalized_rmse": aggregate([case["metrics"]["normalized_rmse"] for case in cases]),
        "raw_duration_delta_seconds": aggregate([case["timeline"]["raw_duration_delta_seconds"] for case in cases]),
    }


def validate_bindings(
    *,
    corpus: dict[str, Any],
    metric_policy: dict[str, Any],
    candidate_policy: dict[str, Any],
    materialization: dict[str, Any],
    baseline: dict[str, Any],
) -> None:
    bindings = candidate_policy["bindings"]
    if sha256_path(CORPUS_FIXTURE) != bindings["corpus_fixture_sha256"]:
        raise ValueError("Candidate policy corpus SHA mismatch.")
    if sha256_path(METRIC_POLICY) != bindings["objective_metric_policy_sha256"]:
        raise ValueError("Candidate policy metric policy SHA mismatch.")
    if baseline["provenance"]["raw_baseline_manifest_sha256"] != bindings["raw_noisy_baseline_sha256"]:
        raise ValueError("Candidate policy raw baseline binding mismatch.")
    if corpus["corpus_id"] != bindings["corpus_id"]:
        raise ValueError("Candidate policy corpus id mismatch.")
    if metric_policy["policy_id"] != bindings["objective_metric_policy_id"]:
        raise ValueError("Candidate policy metric id mismatch.")
    if materialization["corpus_id"] != corpus["corpus_id"] or baseline["corpus_id"] != corpus["corpus_id"]:
        raise ValueError("Corpus id mismatch across frozen evidence.")
    if int(bindings["required_cases"]) != 40 or len(corpus["cases"]) != 40 or len(baseline["cases"]) != 40:
        raise ValueError("Candidate comparison requires exact 40-case frozen corpus.")


def timeline_normalize(
    samples: np.ndarray,
    *,
    target_frames: int,
    sample_rate: int,
    max_delta_seconds: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    raw_delta_frames = int(samples.size) - int(target_frames)
    raw_delta_seconds = raw_delta_frames / float(sample_rate)
    if abs(raw_delta_seconds) > float(max_delta_seconds) + 1e-12:
        raise ValueError(
            f"Candidate duration delta {raw_delta_seconds:.9f}s supera límite precomprometido {max_delta_seconds:.9f}s."
        )
    normalized, audit = right_tail_normalize(samples, target_frame_count=target_frames, padding_value=0.0)
    audit["raw_duration_delta_seconds"] = round(raw_delta_seconds, 8)
    audit["max_abs_raw_duration_delta_seconds"] = float(max_delta_seconds)
    return normalized, audit


def main() -> int:
    corpus = json.loads(CORPUS_FIXTURE.read_text(encoding="utf-8"))
    metric_policy = json.loads(METRIC_POLICY.read_text(encoding="utf-8"))
    candidate_policy = json.loads(CANDIDATE_POLICY.read_text(encoding="utf-8"))
    materialization = json.loads(MATERIALIZATION.read_text(encoding="utf-8"))
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    validate_bindings(
        corpus=corpus,
        metric_policy=metric_policy,
        candidate_policy=candidate_policy,
        materialization=materialization,
        baseline=baseline,
    )

    candidates = {candidate["id"]: candidate for candidate in candidate_policy["candidates"]}
    expected_ids = {
        "preserve_noisy_control_v1",
        "ffmpeg_afftdn_fixed_v1",
        "deepfilternet_0_5_6_compensated_v1",
    }
    if set(candidates) != expected_ids:
        raise ValueError("Candidate set changed after precommitment.")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise FileNotFoundError("FFmpeg no disponible para evaluation harness.")
    ffmpeg_identity = ffmpeg_version(ffmpeg)
    if candidates["ffmpeg_afftdn_fixed_v1"]["ffmpeg_version_contract"] not in ffmpeg_identity:
        raise ValueError("FFmpeg version no cumple candidate policy.")

    clean_zip = DOWNLOAD_ROOT / corpus["archives"]["clean_testset"]["filename"]
    noisy_zip = DOWNLOAD_ROOT / corpus["archives"]["noisy_testset"]["filename"]
    if not clean_zip.is_file() or not noisy_zip.is_file():
        raise FileNotFoundError("Ejecuta primero validate_phase3_denoise_corpus.py.")
    clean_members = zip_basename_map(clean_zip)
    noisy_members = zip_basename_map(noisy_zip)
    evidence_by_id = {case["id"]: case for case in materialization["cases"]}
    baseline_by_id = {case["id"]: case for case in baseline["cases"]}

    media = candidate_policy["media_contract"]
    sample_rate_contract = int(media["input_sample_rate_hz"])
    max_delta_seconds = float(media["raw_duration_delta_max_seconds"])

    with tempfile.TemporaryDirectory(prefix="video_tunner_phase3_denoise_compare_") as temporary:
        temp = Path(temporary)
        deepfilter_exe = temp / "deep-filter.exe"
        deepfilter_runtime = acquire_deepfilter(candidates["deepfilternet_0_5_6_compensated_v1"], deepfilter_exe)

        results: dict[str, dict[str, Any]] = {}
        preserve_cases: list[dict[str, Any]] = []
        for frozen in corpus["cases"]:
            case_id = frozen["id"]
            baseline_case = baseline_by_id[case_id]
            preserve_cases.append(
                {
                    "id": case_id,
                    "speaker": frozen["speaker"],
                    "noise": frozen["noise"],
                    "snr_db": float(frozen["snr_db"]),
                    "clean_sha256": baseline_case["clean_sha256"],
                    "input_noisy_sha256": baseline_case["noisy_sha256"],
                    "output_sha256": baseline_case["noisy_sha256"],
                    "metrics": dict(baseline_case["metrics"]),
                    "delta_vs_preserve": {"si_sdr_db": 0.0, "stoi": 0.0},
                    "timeline": {
                        "method": "identity",
                        "raw_frame_delta": 0,
                        "raw_duration_delta_seconds": 0.0,
                        "action": "none",
                        "alignment_search_performed": False,
                        "time_shift_performed": False,
                        "level_matching_performed": False,
                    },
                }
            )
        results["preserve_noisy_control_v1"] = {
            "candidate": candidates["preserve_noisy_control_v1"],
            "noisy_cases": preserve_cases,
            "noisy_summary": summarize_noisy(preserve_cases),
            "clean_control": {"required": False, "reason": "identity control; clean input is not redundantly rendered"},
        }

        for candidate_id in ("ffmpeg_afftdn_fixed_v1", "deepfilternet_0_5_6_compensated_v1"):
            candidate = candidates[candidate_id]
            noisy_cases: list[dict[str, Any]] = []
            clean_cases: list[dict[str, Any]] = []

            for frozen in corpus["cases"]:
                case_id = frozen["id"]
                basename = case_id + ".wav"
                evidence = evidence_by_id[case_id]
                clean_data = read_member(clean_zip, clean_members[basename])
                noisy_data = read_member(noisy_zip, noisy_members[basename])
                if sha256_bytes(clean_data) != evidence["clean_sha256"]:
                    raise ValueError(f"{case_id}: clean SHA mismatch before candidate evaluation.")
                if sha256_bytes(noisy_data) != evidence["noisy_sha256"]:
                    raise ValueError(f"{case_id}: noisy SHA mismatch before candidate evaluation.")

                case_root = temp / candidate_id / case_id
                case_root.mkdir(parents=True, exist_ok=True)
                clean_input = case_root / "clean.wav"
                noisy_input = case_root / "noisy.wav"
                clean, clean_rate, clean_frames = pcm16_mono_bytes(clean_data, clean_input)
                noisy, noisy_rate, noisy_frames = pcm16_mono_bytes(noisy_data, noisy_input)
                if clean_rate != sample_rate_contract or noisy_rate != sample_rate_contract:
                    raise ValueError(f"{case_id}: sample rate mismatch.")
                if clean_frames != noisy_frames:
                    raise ValueError(f"{case_id}: clean/noisy frame alignment mismatch.")

                rendered: dict[str, Path] = {}
                for label, source in (("noisy", noisy_input), ("clean", clean_input)):
                    if candidate_id == "ffmpeg_afftdn_fixed_v1":
                        raw_output = case_root / f"{label}_afftdn.wav"
                        render_afftdn(
                            ffmpeg=ffmpeg,
                            source=source,
                            destination=raw_output,
                            filter_spec=str(candidate["filter"]),
                        )
                    else:
                        df_dir = case_root / f"{label}_df_out"
                        raw_output = render_deepfilter(executable=deepfilter_exe, source=source, output_dir=df_dir)
                    rendered[label] = raw_output

                noisy_metric_wav = case_root / "noisy_metric_pcm16.wav"
                clean_metric_wav = case_root / "clean_metric_pcm16.wav"
                noisy_render, noisy_render_rate, _ = decode_candidate_to_pcm16(
                    ffmpeg=ffmpeg,
                    source=rendered["noisy"],
                    destination=noisy_metric_wav,
                )
                clean_render, clean_render_rate, _ = decode_candidate_to_pcm16(
                    ffmpeg=ffmpeg,
                    source=rendered["clean"],
                    destination=clean_metric_wav,
                )
                if noisy_render_rate != sample_rate_contract or clean_render_rate != sample_rate_contract:
                    raise ValueError(f"{case_id}: candidate output sample rate mismatch.")

                noisy_normalized, noisy_timeline = timeline_normalize(
                    noisy_render,
                    target_frames=clean_frames,
                    sample_rate=sample_rate_contract,
                    max_delta_seconds=max_delta_seconds,
                )
                clean_normalized, clean_timeline = timeline_normalize(
                    clean_render,
                    target_frames=clean_frames,
                    sample_rate=sample_rate_contract,
                    max_delta_seconds=max_delta_seconds,
                )

                noisy_metrics = compute_paired_objective_metrics(
                    clean,
                    noisy_normalized,
                    sample_rate_hz=sample_rate_contract,
                )
                clean_metrics = compute_clean_preservation_metrics(
                    clean,
                    clean_normalized,
                    sample_rate_hz=sample_rate_contract,
                )
                preserve_metrics = baseline_by_id[case_id]["metrics"]
                noisy_cases.append(
                    {
                        "id": case_id,
                        "speaker": frozen["speaker"],
                        "noise": frozen["noise"],
                        "snr_db": float(frozen["snr_db"]),
                        "clean_sha256": evidence["clean_sha256"],
                        "input_noisy_sha256": evidence["noisy_sha256"],
                        "raw_output_sha256": sha256_path(rendered["noisy"]),
                        "metric_pcm16_sha256": sha256_path(noisy_metric_wav),
                        "metrics": noisy_metrics,
                        "delta_vs_preserve": {
                            "si_sdr_db": round(noisy_metrics["si_sdr_db"] - preserve_metrics["si_sdr_db"], 8),
                            "stoi": round(noisy_metrics["stoi"] - preserve_metrics["stoi"], 8),
                        },
                        "timeline": noisy_timeline,
                    }
                )
                clean_cases.append(
                    {
                        "id": case_id,
                        "speaker": frozen["speaker"],
                        "clean_sha256": evidence["clean_sha256"],
                        "raw_output_sha256": sha256_path(rendered["clean"]),
                        "metric_pcm16_sha256": sha256_path(clean_metric_wav),
                        "metrics": clean_metrics,
                        "timeline": clean_timeline,
                    }
                )

            if len(noisy_cases) != 40 or len(clean_cases) != 40:
                raise ValueError(f"{candidate_id}: comparison incompleta.")
            results[candidate_id] = {
                "candidate": candidate,
                "noisy_cases": noisy_cases,
                "noisy_summary": summarize_noisy(noisy_cases),
                "clean_control": {
                    "required": True,
                    "cases": clean_cases,
                    "summary": summarize_clean(clean_cases),
                },
            }

    report = {
        "schema_version": 1,
        "record_type": "denoiser_candidate_objective_comparison",
        "status": "objective_comparison_complete",
        "valid": True,
        "policy_id": candidate_policy["policy_id"],
        "bindings": {
            "candidate_policy_sha256": sha256_path(CANDIDATE_POLICY),
            "corpus_fixture_sha256": sha256_path(CORPUS_FIXTURE),
            "metric_policy_sha256": sha256_path(METRIC_POLICY),
            "materialization_evidence_sha256": sha256_path(MATERIALIZATION),
            "baseline_evidence_sha256": sha256_path(BASELINE),
            "raw_noisy_baseline_sha256": candidate_policy["bindings"]["raw_noisy_baseline_sha256"],
        },
        "runtime": {
            "ffmpeg": ffmpeg_identity,
            "deepfilternet": deepfilter_runtime,
        },
        "candidate_count": len(results),
        "required_noisy_cases_per_candidate": 40,
        "required_clean_controls_per_treatment_candidate": 40,
        "results": results,
        "interpretation": {
            "descriptive_objective_comparison_only": True,
            "objective_metrics_are_auxiliary_only": True,
            "winner_label": None,
            "acceptance_thresholds_defined": False,
            "candidate_selection_authorized": False,
            "denoiser_selected": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "human_perceptual_ab_required_before_any_selection_or_authorization": True,
            "auto_apply": False,
        },
    }
    OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("PHASE3_DENOISER_COMPARISON_CANDIDATES=3")
    for candidate_id in (
        "preserve_noisy_control_v1",
        "ffmpeg_afftdn_fixed_v1",
        "deepfilternet_0_5_6_compensated_v1",
    ):
        overall = report["results"][candidate_id]["noisy_summary"]["overall"]
        print(f"PHASE3_DENOISER={candidate_id} CASES={overall['case_count']} SISDR={overall['si_sdr_db']['mean']} STOI={overall['stoi']['mean']}")
        if candidate_id != "preserve_noisy_control_v1":
            clean_summary = report["results"][candidate_id]["clean_control"]["summary"]
            print(
                f"PHASE3_DENOISER_CLEAN={candidate_id} CASES={clean_summary['case_count']} "
                f"STOI={clean_summary['stoi']['mean']} NRMSE={clean_summary['normalized_rmse']['mean']}"
            )
    print("PHASE3_DENOISER_OBJECTIVE_COMPARISON=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
