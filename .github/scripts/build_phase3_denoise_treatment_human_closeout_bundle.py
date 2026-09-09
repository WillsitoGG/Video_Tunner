from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
import wave
import zipfile
from pathlib import Path
from typing import Any

from video_tunner.approval import sha256_path
from video_tunner.denoise_execution_authorization import build_denoise_execution_authorization
from video_tunner.denoise_plan import build_denoise_plan_proposal
from video_tunner.denoise_post_render_verification import build_denoise_post_render_verification
from video_tunner.denoise_render import render_denoised_media
from video_tunner.denoise_treatment_human_closeout import build_pending_integrated_review_template
from video_tunner.tools import resolve_tool


REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMMIT = REPO_ROOT / "Validation" / "phase3-denoise-treatment-human-closeout-precommit.json"
CORPUS = REPO_ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
MATERIALIZATION = REPO_ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
SELECTION = REPO_ROOT / "Validation" / "phase3-denoiser-selection-review.json"
DOWNLOAD_ROOT = REPO_ROOT / ".phase3_denoise_corpus_download"
PUBLIC_BUNDLE = REPO_ROOT / "phase3-denoise-treatment-human-closeout-bundle"
TECHNICAL_EVIDENCE = REPO_ROOT / "phase3-denoise-treatment-human-bundle-technical.json"
WORK_ROOT = REPO_ROOT / ".phase3_6k_closeout_work"
QUALITY_SHA = hashlib.sha256(b"phase3-6k-public-evaluation-fixture-quality-binding-v1").hexdigest()
SPEECH_SHA = hashlib.sha256(b"phase3-6k-public-evaluation-fixture-speech-binding-v1").hexdigest()

FORBIDDEN_PUBLIC_TOKENS = (
    "deepfilternet",
    "deep-filter",
    "deepfilternet_0_5_6_compensated_v1",
    "treatment_label_by_case",
    "treatment_label",
    "selected_candidate_id",
    "p232_",
    "p257_",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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


def wav_contract(data: bytes) -> dict[str, Any]:
    with wave.open(io.BytesIO(data), "rb") as wav:
        channels = int(wav.getnchannels())
        sample_width = int(wav.getsampwidth())
        rate = int(wav.getframerate())
        frames = int(wav.getnframes())
    if channels != 1 or sample_width != 2 or rate != 48000 or frames <= 0:
        raise ValueError("Phase 3.6k listening WAV debe ser PCM16 mono 48 kHz no vacío.")
    return {
        "channels": channels,
        "sample_rate_hz": rate,
        "codec": "pcm_s16le",
        "frame_count": frames,
        "duration_seconds": round(frames / 48000.0, 6),
    }


def public_file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(PUBLIC_BUNDLE).as_posix(),
        "sha256": sha256_bytes(data),
        **wav_contract(data),
    }


def run_checked(command: list[str], *, label: str) -> None:
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{label} falló ({completed.returncode}).\n"
            f"stdout={completed.stdout[-3000:]}\n"
            f"stderr={completed.stderr[-3000:]}"
        )


def write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha256_path(path)


def noise_audit_fixture(output_sha: str, *, case_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "record_type": "noise_evidence_audit",
        "status": "noise_measurement_complete",
        "valid": True,
        "evidence_sufficient": True,
        "quality_binding": {
            "quality_audit_sha256": QUALITY_SHA,
            "required_quality_status": "quality_audit_complete",
            "output_sha256": output_sha,
        },
        "window_evidence": {"speech_evidence_sha256": SPEECH_SHA},
        "coverage": {"non_speech_window_count": 2, "non_speech_seconds": 2.5},
        "measurements": {"non_speech_energy": {"median_rms_dbfs": -42.0}},
        "interpretation": {
            "metric_scope": f"Phase 3.6k public evaluation execution-gate fixture for {case_id}",
            "threshold_note": "Fixture-only coverage gate. No dBFS value is a denoise threshold or claim that treatment is needed.",
        },
        "treatment_policy": {
            "denoise_evaluated": False,
            "denoise_authorized": False,
            "filter_selected": False,
            "parameters_defined": False,
            "normalization_authorized": False,
            "join_smoothing_authorized": False,
        },
        "executable": False,
        "treatment_authorized": False,
        "auto_apply": False,
    }


def decode_audio_to_pcm48k_mono(ffmpeg: Path, source: Path, destination: Path) -> dict[str, Any]:
    run_checked(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-c:a",
            "pcm_s16le",
            str(destination),
        ],
        label=f"Decode listening audio {source.name}",
    )
    return wav_contract(destination.read_bytes())


def build_source_wrapper(ffmpeg: Path, noisy_wav: Path, destination: Path) -> None:
    run_checked(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:r=25",
            "-i",
            str(noisy_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "mpeg4",
            "-q:v",
            "5",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ac",
            "1",
            "-ar",
            "48000",
            "-shortest",
            str(destination),
        ],
        label=f"Build public source wrapper {destination.name}",
    )


def assert_public_blind(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    leaks = [token for token in FORBIDDEN_PUBLIC_TOKENS if token in text]
    if leaks:
        raise ValueError(f"{path.name}: public blinding leak: {leaks}")


def technical_snapshot(verification: dict[str, Any]) -> dict[str, Any]:
    source = verification.get("source")
    output = verification.get("output")
    if not isinstance(source, dict) or not isinstance(output, dict):
        raise ValueError("Verifier PASS sin source/output snapshot.")
    return {
        "record_type": verification.get("record_type"),
        "status": verification.get("status"),
        "valid_evidence": verification.get("valid_evidence"),
        "technical_pass": verification.get("technical_pass"),
        "human_perceptual_review_required": verification.get("human_perceptual_review_required"),
        "human_pass": verification.get("human_pass"),
        "blockers": verification.get("blockers"),
        "product_default": verification.get("product_default"),
        "auto_apply": verification.get("auto_apply"),
        "decoded_video_equal": source.get("decoded_video_sha256") == output.get("decoded_video_sha256"),
        "source_frames": source.get("decoded_audio_frames_48k_mono"),
        "output_frames": output.get("decoded_audio_frames_48k_mono"),
    }


def main() -> int:
    precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    materialization = json.loads(MATERIALIZATION.read_text(encoding="utf-8"))
    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    precommit_sha = sha256_path(PRECOMMIT)
    selection_sha = sha256_path(SELECTION)

    expected_precommit_sha = precommit["upstream_bindings"]["case_selection_policy_sha256"]
    phase3e_policy = REPO_ROOT / precommit["upstream_bindings"]["case_selection_source"]
    if sha256_path(phase3e_policy) != expected_precommit_sha:
        raise ValueError("Phase 3.6e policy SHA changed after 3.6k precommit.")
    if selection.get("selected_candidate_id") != precommit["upstream_bindings"]["selected_candidate_id"]:
        raise ValueError("Selected candidate changed after 3.6k precommit.")

    clean_zip = DOWNLOAD_ROOT / corpus["archives"]["clean_testset"]["filename"]
    noisy_zip = DOWNLOAD_ROOT / corpus["archives"]["noisy_testset"]["filename"]
    if not clean_zip.is_file() or not noisy_zip.is_file():
        raise FileNotFoundError("Corpus archives missing; run validate_phase3_denoise_corpus.py first.")
    clean_members = zip_basename_map(clean_zip)
    noisy_members = zip_basename_map(noisy_zip)
    materialized = {case["id"]: case for case in materialization["cases"]}

    if PUBLIC_BUNDLE.exists():
        shutil.rmtree(PUBLIC_BUNDLE)
    if WORK_ROOT.exists():
        shutil.rmtree(WORK_ROOT)
    PUBLIC_BUNDLE.mkdir(parents=True)
    WORK_ROOT.mkdir(parents=True)
    TECHNICAL_EVIDENCE.unlink(missing_ok=True)

    ffmpeg = Path(resolve_tool("ffmpeg")).resolve()
    selected_cases = precommit["case_selection"]["cases_in_required_order"]
    labels = precommit["blinding_contract"]["treatment_label_by_case"]
    public_cases: list[dict[str, Any]] = []
    technical_cases: list[dict[str, Any]] = []

    for index, case in enumerate(selected_cases, start=1):
        case_id = case["id"]
        basename = case_id + ".wav"
        if basename not in clean_members or basename not in noisy_members:
            raise FileNotFoundError(f"{case_id}: paired source missing from verified archives.")
        clean_data = read_member(clean_zip, clean_members[basename])
        noisy_data = read_member(noisy_zip, noisy_members[basename])
        evidence = materialized[case_id]
        if sha256_bytes(clean_data) != evidence["clean_sha256"] or sha256_bytes(noisy_data) != evidence["noisy_sha256"]:
            raise ValueError(f"{case_id}: source SHA mismatch against frozen materialization.")
        wav_contract(clean_data)
        wav_contract(noisy_data)

        case_work = WORK_ROOT / case_id
        case_work.mkdir()
        noisy_wav = case_work / "noisy.wav"
        clean_wav = case_work / "clean.wav"
        source_mp4 = case_work / "source.mp4"
        rendered_mp4 = case_work / "rendered.mp4"
        noisy_wav.write_bytes(noisy_data)
        clean_wav.write_bytes(clean_data)
        build_source_wrapper(ffmpeg, noisy_wav, source_mp4)
        source_sha = sha256_path(source_mp4)

        audit = noise_audit_fixture(source_sha, case_id=case_id)
        noise_sha = write_json(case_work / "noise_audit.json", audit)
        plan = build_denoise_plan_proposal(
            audit,
            selection,
            noise_audit_sha256=noise_sha,
            selection_review_sha256=selection_sha,
            current_output_sha256=source_sha,
        )
        plan_sha = write_json(case_work / "denoise_plan.json", plan)
        authorization = build_denoise_execution_authorization(
            audit,
            selection,
            plan,
            decision="APPROVE",
            actor=precommit["integrated_fixture_contract"]["authorization"]["actor"],
            reason=precommit["integrated_fixture_contract"]["authorization"]["reason"],
            noise_audit_sha256=noise_sha,
            selection_review_sha256=selection_sha,
            plan_sha256=plan_sha,
            current_output_sha256=source_sha,
            created_utc="2026-09-09T10:50:00+00:00",
        )
        authorization_sha = write_json(case_work / "denoise_authorization.json", authorization)
        render_result = render_denoised_media(
            source_mp4,
            audit,
            selection,
            plan,
            authorization,
            rendered_mp4,
            noise_audit_sha256=noise_sha,
            selection_review_sha256=selection_sha,
            plan_sha256=plan_sha,
            authorization_sha256=authorization_sha,
        )
        render_sha = write_json(case_work / "denoise_render_result.json", render_result)
        verification = build_denoise_post_render_verification(
            source_mp4,
            rendered_mp4,
            audit,
            selection,
            plan,
            authorization,
            render_result,
            noise_audit_sha256=noise_sha,
            selection_review_sha256=selection_sha,
            plan_sha256=plan_sha,
            authorization_sha256=authorization_sha,
            render_result_sha256=render_sha,
        )
        verification_sha = write_json(case_work / "denoise_post_render_verification.json", verification)
        snapshot = technical_snapshot(verification)
        if snapshot["status"] != "technical_denoise_pass" or snapshot["technical_pass"] is not True:
            raise ValueError(f"{case_id}: technical verifier did not PASS: {snapshot}")
        if snapshot["valid_evidence"] is not True or snapshot["blockers"] not in ([], None):
            raise ValueError(f"{case_id}: verifier evidence invalid/blocking.")
        if snapshot["human_pass"] is not False or snapshot["human_perceptual_review_required"] is not True:
            raise ValueError(f"{case_id}: verifier prematurely claims human PASS.")
        if snapshot["decoded_video_equal"] is not True or snapshot["source_frames"] != snapshot["output_frames"]:
            raise ValueError(f"{case_id}: integrated video/audio timeline contract failed.")

        preserve_wav = case_work / "preserve_decoded.wav"
        treatment_wav = case_work / "treatment_decoded.wav"
        preserve_contract = decode_audio_to_pcm48k_mono(ffmpeg, source_mp4, preserve_wav)
        treatment_contract = decode_audio_to_pcm48k_mono(ffmpeg, rendered_mp4, treatment_wav)
        if preserve_contract["frame_count"] != treatment_contract["frame_count"]:
            raise ValueError(f"{case_id}: A/B decoded frame counts differ.")

        public_case = f"case_{index:02d}"
        public_dir = PUBLIC_BUNDLE / public_case
        public_dir.mkdir()
        public_clean = public_dir / "clean_reference.wav"
        public_a = public_dir / "A.wav"
        public_b = public_dir / "B.wav"
        public_clean.write_bytes(clean_data)
        label = labels[case_id]
        shutil.copyfile(treatment_wav if label == "A" else preserve_wav, public_a)
        shutil.copyfile(treatment_wav if label == "B" else preserve_wav, public_b)
        clean_record = public_file_record(public_clean)
        a_record = public_file_record(public_a)
        b_record = public_file_record(public_b)

        preserve_sha = sha256_path(preserve_wav)
        treatment_sha = sha256_path(treatment_wav)
        if (a_record["sha256"] if label == "A" else b_record["sha256"]) != treatment_sha:
            raise ValueError(f"{case_id}: public treatment label SHA mismatch.")
        if (b_record["sha256"] if label == "A" else a_record["sha256"]) != preserve_sha:
            raise ValueError(f"{case_id}: public preserve label SHA mismatch.")
        if a_record["sha256"] == b_record["sha256"]:
            raise ValueError(f"{case_id}: A/B are byte-identical; closeout comparison invalid.")

        public_cases.append(
            {
                "public_case": public_case,
                "clean_reference": clean_record,
                "A": a_record,
                "B": b_record,
            }
        )
        technical_cases.append(
            {
                "case_id": case_id,
                "public_case": public_case,
                "treatment_label": label,
                "technical_verification_sha256": verification_sha,
                "source_media_sha256": source_sha,
                "rendered_media_sha256": sha256_path(rendered_mp4),
                "preserve_wav_sha256": preserve_sha,
                "treatment_wav_sha256": treatment_sha,
                "clean_reference_wav_sha256": sha256_bytes(clean_data),
                "A_wav_sha256": a_record["sha256"],
                "B_wav_sha256": b_record["sha256"],
                "technical_verification": snapshot,
                "fixture_authorization": {
                    "actor": authorization["actor"],
                    "counts_as_real_guille_authorization": False,
                },
            }
        )
        print(
            f"PHASE3_6K_CASE={public_case} TECHNICAL_PASS=1 "
            f"SOURCE_FRAMES={snapshot['source_frames']} OUTPUT_FRAMES={snapshot['output_frames']}"
        )

    manifest = {
        "schema_version": 1,
        "record_type": "denoise_integrated_blinded_human_bundle_manifest",
        "phase": "3.6k",
        "blinded": True,
        "case_count": 10,
        "comparison_count": 10,
        "sample_rate_hz": 48000,
        "channels": 1,
        "codec": "pcm_s16le",
        "instructions_file": "README.txt",
        "review_template_file": "human_review_decisions.json",
        "cases": public_cases,
        "capabilities": {
            "real_user_authorization_created": False,
            "product_default_changed": False,
            "auto_apply": False,
            "stereo_or_multichannel_generalized": False,
        },
    }
    manifest_path = PUBLIC_BUNDLE / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_sha = sha256_path(manifest_path)

    review = build_pending_integrated_review_template(
        precommit=precommit,
        precommit_sha256=precommit_sha,
        bundle_manifest_sha256=manifest_sha,
    )
    private_to_public = {case["id"]: f"case_{index:02d}" for index, case in enumerate(selected_cases, start=1)}
    for decision in review["decisions"]:
        decision["case_id"] = private_to_public[decision["case_id"]]
    review["note"] = "Public blinded Phase 3.6k template. Return completed decisions; repository-side finalization remaps public labels before validation."
    review_path = PUBLIC_BUNDLE / "human_review_decisions.json"
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    readme = """PHASE 3.6k — BLINDED INTEGRATED DENOISE CLOSEOUT\n\nThis bundle contains 10 public evaluation cases. For each case:\n1. Listen to clean_reference.wav only to understand the intended speech and check speech integrity.\n2. Listen to A.wav and B.wav fully before deciding.\n3. Fill the matching entry in human_review_decisions.json.\n\nFor each case record:\n- preference: A, B, or NO_PREFERENCE; choose the version you would want in the finished video considering background noise, naturalness and intelligibility together.\n- A/B speech_integrity: PASS unless a phoneme, word, consonant attack, ending, or intelligible speech content is removed, clipped or materially damaged versus clean_reference.wav.\n- A/B artifact: FAIL only for unacceptable metallic/musical noise, warbling, pumping, gating, transient or other processing artifacts. Remaining background noise is not by itself an artifact failure.\n- reason: required; brief text is enough.\n\nUse headphones if practical. A/B mapping is intentionally withheld. Do not infer it from filenames or metadata.\n\nThe 10 selectable pairs were generated only after all 10 integrated cases passed the independent technical verifier. This human review does not authorize any personal/user media, change the product default, enable automatic application or generalize stereo/multichannel support.\n"""
    readme_path = PUBLIC_BUNDLE / "README.txt"
    readme_path.write_text(readme, encoding="utf-8")

    for text_path in (manifest_path, review_path, readme_path):
        assert_public_blind(text_path)
    wav_files = sorted(PUBLIC_BUNDLE.rglob("*.wav"))
    if len(wav_files) != 30:
        raise ValueError(f"Public bundle incomplete: {len(wav_files)} WAV != 30.")

    technical_evidence = {
        "schema_version": 1,
        "record_type": "phase3_denoise_treatment_human_bundle_technical_evidence",
        "phase": "3.6k",
        "status": "TECHNICAL_BUNDLE_READY_FOR_HUMAN_REVIEW",
        "precommit_sha256": precommit_sha,
        "public_bundle_manifest_sha256": manifest_sha,
        "case_count": 10,
        "technical_pass_count": 10,
        "technical_fail_count": 0,
        "invalid_or_stale_count": 0,
        "cases": technical_cases,
        "capabilities": {
            "real_guille_authorization_created": False,
            "real_guille_media_processed": False,
            "product_default": "preserve",
            "auto_apply": False,
            "stereo_or_multichannel_generalized": False,
        },
        "note": "Technical evidence only. Every listening pair comes from the full fixture-only plan/authorization/renderer/verifier chain. No human listening decision is recorded here.",
    }
    write_json(TECHNICAL_EVIDENCE, technical_evidence)

    print(f"PHASE3_6K_PRECOMMIT_SHA256={precommit_sha}")
    print(f"PHASE3_6K_PUBLIC_MANIFEST_SHA256={manifest_sha}")
    print("PHASE3_6K_TECHNICAL_PASS_COUNT=10/10")
    print("PHASE3_6K_TECHNICAL_FAIL_COUNT=0")
    print("PHASE3_6K_INVALID_OR_STALE_COUNT=0")
    print(f"PHASE3_6K_PUBLIC_WAV_FILES={len(wav_files)}")
    print("PHASE3_6K_PUBLIC_BLINDING_LEAKS=0")
    print("PHASE3_6K_HUMAN_LISTENING_COMPLETED=0")
    print("PHASE3_6K_BUNDLE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
