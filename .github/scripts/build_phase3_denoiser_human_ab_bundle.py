from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import urllib.request
import wave
import zipfile
from pathlib import Path
from typing import Any

import numpy as np

from video_tunner.denoise_human_review import build_pending_review_template


REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
MATERIALIZATION = REPO_ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
CANDIDATE_POLICY = REPO_ROOT / "tests" / "fixtures" / "phase3_denoiser_candidate_comparison_policy_v1.json"
HUMAN_POLICY = REPO_ROOT / "tests" / "fixtures" / "phase3_denoiser_human_ab_policy_v1.json"
DOWNLOAD_ROOT = REPO_ROOT / ".phase3_denoise_corpus_download"
BUNDLE_ROOT = REPO_ROOT / "phase3-denoiser-human-ab-bundle"

FORBIDDEN_PUBLIC_TOKENS = (
    "deepfilternet",
    "deep-filter",
    "afftdn",
    "ffmpeg_afftdn",
    "preserve_noisy_control",
    "treatment_candidate",
    "control_candidate",
    "treatment_label",
)


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
        result: dict[str, str] = {}
        for member in archive.namelist():
            if member.endswith("/"):
                continue
            basename = Path(member).name
            if basename in result:
                raise ValueError(f"Basename duplicado en {archive_path.name}: {basename}")
            result[basename] = member
        return result


def read_member(archive_path: Path, member: str) -> bytes:
    with zipfile.ZipFile(archive_path) as archive:
        return archive.read(member)


def wav_pcm16_mono(data: bytes) -> tuple[np.ndarray, int, int]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        if wav.getnchannels() != 1 or wav.getsampwidth() != 2:
            raise ValueError("3.6e requiere WAV PCM16 mono.")
        rate = int(wav.getframerate())
        frames = int(wav.getnframes())
        raw = wav.readframes(frames)
    samples = np.frombuffer(raw, dtype="<i2").copy()
    if samples.size != frames:
        raise ValueError("Frame count PCM no coincide con cabecera WAV.")
    return samples, rate, frames


def write_pcm16_mono(path: Path, samples: np.ndarray, sample_rate_hz: int) -> None:
    values = np.asarray(samples, dtype="<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(sample_rate_hz))
        wav.writeframes(values.tobytes())


def normalize_right_tail(samples: np.ndarray, target_frames: int) -> np.ndarray:
    current = int(samples.size)
    if current == target_frames:
        return samples.copy()
    if current > target_frames:
        return samples[:target_frames].copy()
    return np.pad(samples, (0, target_frames - current), mode="constant", constant_values=0)


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            "Comando externo falló: " + " ".join(command) + "\nSTDOUT:\n" + completed.stdout + "\nSTDERR:\n" + completed.stderr
        )


def download_pinned(url: str, destination: Path, expected_sha256: str, expected_size: int) -> None:
    if destination.exists() and sha256_path(destination) == expected_sha256 and destination.stat().st_size == expected_size:
        return
    request = urllib.request.Request(url, headers={"User-Agent": "Video_Tunner Phase3.6e bundle builder"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    if destination.stat().st_size != expected_size:
        raise ValueError("DeepFilterNet asset size mismatch.")
    if sha256_path(destination) != expected_sha256:
        raise ValueError("DeepFilterNet asset SHA256 mismatch.")


def find_deepfilter_output(output_dir: Path, input_name: str) -> Path:
    candidates = sorted(output_dir.glob("*.wav"))
    if len(candidates) != 1:
        raise ValueError(f"DeepFilterNet debía producir exactamente un WAV; encontrados {len(candidates)} para {input_name}")
    return candidates[0]


def assert_public_text_blind(text: str, *, label: str) -> None:
    lowered = text.lower()
    leaks = [token for token in FORBIDDEN_PUBLIC_TOKENS if token in lowered]
    if leaks:
        raise ValueError(f"{label} filtra información ciega: {leaks}")


def public_file_record(path: Path, *, relative_to: Path) -> dict[str, Any]:
    data = path.read_bytes()
    samples, rate, frames = wav_pcm16_mono(data)
    if rate != 48000 or samples.size != frames:
        raise ValueError(f"{path.name}: media contract roto.")
    return {
        "path": path.relative_to(relative_to).as_posix(),
        "sha256": sha256_bytes(data),
        "sample_rate_hz": rate,
        "channels": 1,
        "codec": "pcm_s16le",
        "frame_count": frames,
        "duration_seconds": round(frames / rate, 6),
    }


def main() -> int:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    materialization = json.loads(MATERIALIZATION.read_text(encoding="utf-8"))
    candidate_policy = json.loads(CANDIDATE_POLICY.read_text(encoding="utf-8"))
    human_policy = json.loads(HUMAN_POLICY.read_text(encoding="utf-8"))

    human_policy_sha = sha256_path(HUMAN_POLICY)
    materialized = {case["id"]: case for case in materialization["cases"]}
    selected = human_policy["case_selection"]["cases_in_selection_rank_order"]
    if len(selected) != 10 or len({case["id"] for case in selected}) != 10:
        raise ValueError("Policy 3.6e no contiene exactamente 10 casos únicos.")

    clean_zip = DOWNLOAD_ROOT / corpus["archives"]["clean_testset"]["filename"]
    noisy_zip = DOWNLOAD_ROOT / corpus["archives"]["noisy_testset"]["filename"]
    if not clean_zip.is_file() or not noisy_zip.is_file():
        raise FileNotFoundError("Corpus no materializado; ejecuta validate_phase3_denoise_corpus.py primero.")
    clean_members = zip_basename_map(clean_zip)
    noisy_members = zip_basename_map(noisy_zip)

    candidates = {item["id"]: item for item in candidate_policy["candidates"]}
    df = candidates["deepfilternet_0_5_6_compensated_v1"]
    aff = candidates["ffmpeg_afftdn_fixed_v1"]
    if human_policy["bindings"]["deepfilternet_asset_sha256"] != df["asset_sha256"]:
        raise ValueError("Human policy DeepFilterNet binding mismatch.")

    if BUNDLE_ROOT.exists():
        shutil.rmtree(BUNDLE_ROOT)
    BUNDLE_ROOT.mkdir(parents=True)
    work = REPO_ROOT / ".phase3e_human_bundle_work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    deepfilter_exe = work / "deep-filter.exe"
    download_pinned(df["asset_url"], deepfilter_exe, df["asset_sha256"], int(df["asset_size_bytes"]))

    pair_by_public = {pair["public_pair_label"]: pair for pair in human_policy["pairwise_comparisons"]}
    public_cases: list[dict[str, Any]] = []
    private_expected: dict[tuple[str, str], dict[str, str]] = {}

    for case_index, case in enumerate(selected, start=1):
        case_id = case["id"]
        evidence = materialized[case_id]
        basename = case_id + ".wav"
        clean_data = read_member(clean_zip, clean_members[basename])
        noisy_data = read_member(noisy_zip, noisy_members[basename])
        if sha256_bytes(clean_data) != evidence["clean_sha256"] or sha256_bytes(noisy_data) != evidence["noisy_sha256"]:
            raise ValueError(f"{case_id}: source SHA mismatch contra materialización congelada.")

        clean_samples, clean_rate, clean_frames = wav_pcm16_mono(clean_data)
        noisy_samples, noisy_rate, noisy_frames = wav_pcm16_mono(noisy_data)
        if clean_rate != 48000 or noisy_rate != 48000 or clean_frames != noisy_frames:
            raise ValueError(f"{case_id}: source timeline/media contract roto.")

        case_dir = BUNDLE_ROOT / f"case_{case_index:02d}"
        case_dir.mkdir()
        clean_path = case_dir / "clean_reference.wav"
        noisy_path = work / f"{case_id}_noisy.wav"
        clean_path.write_bytes(clean_data)
        noisy_path.write_bytes(noisy_data)

        aff_path = work / f"{case_id}_afftdn.wav"
        run_checked([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(noisy_path), "-af", aff["filter"], "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(aff_path),
        ])
        aff_samples, aff_rate, aff_frames = wav_pcm16_mono(aff_path.read_bytes())
        if aff_rate != 48000 or aff_frames != noisy_frames:
            raise ValueError(f"{case_id}: afftdn cambió frame count ({aff_frames} != {noisy_frames}).")

        df_input = work / f"df_{case_id}.wav"
        df_input.write_bytes(noisy_data)
        df_output_dir = work / f"df_out_{case_id}"
        df_output_dir.mkdir()
        run_checked([str(deepfilter_exe), "--compensate-delay", "--output-dir", str(df_output_dir), str(df_input)])
        df_raw_path = find_deepfilter_output(df_output_dir, df_input.name)
        df_samples, df_rate, df_frames = wav_pcm16_mono(df_raw_path.read_bytes())
        if df_rate != 48000:
            raise ValueError(f"{case_id}: DeepFilterNet sample rate inesperado {df_rate}.")
        delta_seconds = abs(df_frames - noisy_frames) / 48000.0
        if delta_seconds > float(candidate_policy["media_contract"]["raw_duration_delta_max_seconds"]) + 1e-12:
            raise ValueError(f"{case_id}: DeepFilterNet duration delta {delta_seconds:.6f}s excede policy.")
        df_normalized_path = work / f"{case_id}_deepfilter_normalized.wav"
        write_pcm16_mono(df_normalized_path, normalize_right_tail(df_samples, noisy_frames), 48000)
        normalized_samples, normalized_rate, normalized_frames = wav_pcm16_mono(df_normalized_path.read_bytes())
        if normalized_rate != 48000 or normalized_frames != noisy_frames:
            raise ValueError(f"{case_id}: DeepFilterNet right-tail normalization falló.")

        candidate_paths = {
            "preserve_noisy_control_v1": noisy_path,
            "ffmpeg_afftdn_fixed_v1": aff_path,
            "deepfilternet_0_5_6_compensated_v1": df_normalized_path,
        }
        public_comparisons: list[dict[str, Any]] = []
        for public_label in human_policy["blinding_contract"]["public_bundle_pair_labels"]:
            pair = pair_by_public[public_label]
            treatment_label = pair["treatment_label_by_case"][case_id]
            preserve_label = "B" if treatment_label == "A" else "A"
            label_to_candidate = {
                treatment_label: pair["treatment_candidate_id"],
                preserve_label: pair["control_candidate_id"],
            }
            comparison_dir = case_dir / public_label
            comparison_dir.mkdir()
            records = {}
            for label in ("A", "B"):
                destination = comparison_dir / f"{label}.wav"
                shutil.copyfile(candidate_paths[label_to_candidate[label]], destination)
                record = public_file_record(destination, relative_to=BUNDLE_ROOT)
                if record["frame_count"] != noisy_frames:
                    raise ValueError(f"{case_id}/{public_label}/{label}: frame count público inesperado.")
                records[label] = record
            public_comparisons.append({"comparison": public_label, "A": records["A"], "B": records["B"]})
            private_expected[(case_id, public_label)] = {
                "A_sha256": records["A"]["sha256"],
                "B_sha256": records["B"]["sha256"],
                "treatment_label": treatment_label,
            }

        public_cases.append(
            {
                "public_case": f"case_{case_index:02d}",
                "clean_reference": public_file_record(clean_path, relative_to=BUNDLE_ROOT),
                "comparisons": public_comparisons,
            }
        )

    manifest = {
        "schema_version": 1,
        "record_type": "denoiser_blinded_human_ab_bundle_manifest",
        "policy_id": human_policy["policy_id"],
        "policy_sha256": human_policy_sha,
        "blinded": True,
        "case_count": 10,
        "comparison_count": 20,
        "instructions_file": "README.txt",
        "review_template_file": "human_review_decisions.json",
        "cases": public_cases,
        "capabilities": {
            "candidate_selection_authorized": False,
            "denoiser_selected": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }
    manifest_path = BUNDLE_ROOT / "manifest.json"
    manifest_text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    assert_public_text_blind(manifest_text, label="manifest.json")
    manifest_path.write_text(manifest_text, encoding="utf-8")
    manifest_sha = sha256_path(manifest_path)

    review = build_pending_review_template(
        policy=human_policy,
        policy_sha256=human_policy_sha,
        bundle_manifest_sha256=manifest_sha,
    )
    # Replace private case ids with public case labels in the file delivered for listening.
    case_id_to_public = {case["id"]: f"case_{index:02d}" for index, case in enumerate(selected, start=1)}
    for decision in review["decisions"]:
        decision["case_id"] = case_id_to_public[decision["case_id"]]
    review["note"] = "Public blinded template. Return these decisions; the repository-side finalizer remaps public_case to the frozen private case id before validation/unblinding."
    review_path = BUNDLE_ROOT / "human_review_decisions.json"
    review_text = json.dumps(review, indent=2, ensure_ascii=False) + "\n"
    assert_public_text_blind(review_text, label="human_review_decisions.json")
    review_path.write_text(review_text, encoding="utf-8")

    readme = """PHASE 3.6e — BLINDED HUMAN A/B\n\nThis bundle contains 10 cases and 20 blinded A/B comparisons.\nFor each case:\n1. Listen to clean_reference.wav only to understand the intended speech.\n2. Open comparison_1/A.wav and B.wav; listen to both.\n3. Open comparison_2/A.wav and B.wav; listen to both.\n4. Fill human_review_decisions.json.\n\nFor every A/B pair record:\n- preference: A, B, or NO_PREFERENCE. Choose the version you would want in the finished video considering noise reduction, naturalness and intelligibility together.\n- A/B speech_integrity: PASS unless speech is clipped, removed or materially damaged versus clean_reference.wav.\n- A/B artifact: FAIL only for unacceptable processing artifacts (metallic/musical noise, warbling, pumping, gating, transients, etc.). Remaining background noise is not by itself an artifact failure.\n- reason: required, brief text is enough.\n\nUse headphones if practical. Do not try to infer which algorithm is A or B. The bundle intentionally contains no candidate names or A/B key.\n\nA completed human review does not authorize treatment, rendering or auto-apply.\n"""
    assert_public_text_blind(readme, label="README.txt")
    (BUNDLE_ROOT / "README.txt").write_text(readme, encoding="utf-8")

    # Final public leak scan and completeness verification.
    wav_files = sorted(BUNDLE_ROOT.rglob("*.wav"))
    if len(wav_files) != 50:
        raise ValueError(f"Bundle público incompleto: {len(wav_files)} WAV != 50.")
    for text_path in (manifest_path, review_path, BUNDLE_ROOT / "README.txt"):
        assert_public_text_blind(text_path.read_text(encoding="utf-8"), label=text_path.name)
    if set(pair_by_public) != {"comparison_1", "comparison_2"}:
        raise ValueError("Public comparison labels inesperadas.")

    print(f"PHASE3_36E_POLICY_SHA256={human_policy_sha}")
    print(f"PHASE3_36E_BUNDLE_MANIFEST_SHA256={manifest_sha}")
    print(f"PHASE3_36E_CASES={len(public_cases)}")
    print(f"PHASE3_36E_COMPARISONS={sum(len(case['comparisons']) for case in public_cases)}")
    print(f"PHASE3_36E_WAV_FILES={len(wav_files)}")
    print("PHASE3_36E_PUBLIC_BLINDING_LEAKS=0")
    print("PHASE3_DENOISER_HUMAN_AB_BUNDLE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
