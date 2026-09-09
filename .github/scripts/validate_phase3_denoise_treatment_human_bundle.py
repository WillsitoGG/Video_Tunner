from __future__ import annotations

import hashlib
import io
import json
import wave
from pathlib import Path

from video_tunner.denoise_treatment_human_closeout import validate_integrated_bundle_technical_evidence


REPO_ROOT = Path(__file__).resolve().parents[2]
PRECOMMIT = REPO_ROOT / "Validation" / "phase3-denoise-treatment-human-closeout-precommit.json"
PUBLIC_BUNDLE = REPO_ROOT / "phase3-denoise-treatment-human-closeout-bundle"
TECHNICAL_EVIDENCE = REPO_ROOT / "phase3-denoise-treatment-human-bundle-technical.json"
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


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wav_contract(path: Path) -> dict[str, int]:
    with wave.open(str(path), "rb") as wav:
        channels = int(wav.getnchannels())
        width = int(wav.getsampwidth())
        rate = int(wav.getframerate())
        frames = int(wav.getnframes())
    if channels != 1 or width != 2 or rate != 48000 or frames <= 0:
        raise ValueError(f"{path}: listening WAV contract inválido.")
    return {"channels": channels, "sample_rate_hz": rate, "frame_count": frames}


def assert_public_text_blind(path: Path) -> None:
    text = path.read_text(encoding="utf-8").lower()
    leaks = [token for token in FORBIDDEN_PUBLIC_TOKENS if token in text]
    if leaks:
        raise ValueError(f"{path.name}: blinding leak: {leaks}")


def main() -> int:
    precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
    precommit_sha = sha256_path(PRECOMMIT)
    technical = json.loads(TECHNICAL_EVIDENCE.read_text(encoding="utf-8"))
    validated = validate_integrated_bundle_technical_evidence(
        technical_evidence=technical,
        precommit=precommit,
        expected_precommit_sha256=precommit_sha,
    )
    if not validated["valid"] or validated["technical_pass_count"] != 10:
        raise ValueError("Technical evidence validator no acredita 10/10 PASS.")

    manifest_path = PUBLIC_BUNDLE / "manifest.json"
    review_path = PUBLIC_BUNDLE / "human_review_decisions.json"
    readme_path = PUBLIC_BUNDLE / "README.txt"
    for required in (manifest_path, review_path, readme_path):
        if not required.is_file():
            raise FileNotFoundError(f"Public bundle missing {required.name}")
        assert_public_text_blind(required)

    manifest_sha = sha256_path(manifest_path)
    if manifest_sha != validated["public_bundle_manifest_sha256"]:
        raise ValueError("Public manifest SHA no coincide con technical evidence.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("record_type") != "denoise_integrated_blinded_human_bundle_manifest":
        raise ValueError("Public manifest schema/record_type inválido.")
    if manifest.get("phase") != "3.6k" or manifest.get("blinded") is not True:
        raise ValueError("Public manifest no conserva Phase 3.6k/blinded.")
    if manifest.get("case_count") != 10 or manifest.get("comparison_count") != 10:
        raise ValueError("Public manifest no contiene exactamente 10 casos/comparaciones.")
    if manifest.get("sample_rate_hz") != 48000 or manifest.get("channels") != 1 or manifest.get("codec") != "pcm_s16le":
        raise ValueError("Public manifest listening media contract inválido.")

    cases = manifest.get("cases")
    if not isinstance(cases, list) or len(cases) != 10:
        raise ValueError("Public manifest cases inválidos.")
    seen: set[str] = set()
    for index, case in enumerate(cases, start=1):
        expected_public = f"case_{index:02d}"
        if not isinstance(case, dict) or case.get("public_case") != expected_public or expected_public in seen:
            raise ValueError("Public case labels no respetan orden congelado.")
        seen.add(expected_public)
        records = {name: case.get(name) for name in ("clean_reference", "A", "B")}
        for label, record in records.items():
            if not isinstance(record, dict):
                raise ValueError(f"{expected_public}: falta record {label}.")
            path = PUBLIC_BUNDLE / str(record.get("path") or "")
            if not path.is_file():
                raise FileNotFoundError(f"{expected_public}/{label}: file missing.")
            if sha256_path(path) != record.get("sha256"):
                raise ValueError(f"{expected_public}/{label}: SHA mismatch.")
            contract = wav_contract(path)
            if record.get("sample_rate_hz") != 48000 or record.get("channels") != 1 or record.get("codec") != "pcm_s16le":
                raise ValueError(f"{expected_public}/{label}: manifest media contract mismatch.")
            if record.get("frame_count") != contract["frame_count"]:
                raise ValueError(f"{expected_public}/{label}: frame count mismatch.")
        if records["A"]["frame_count"] != records["B"]["frame_count"]:
            raise ValueError(f"{expected_public}: A/B frame counts differ.")
        if records["A"]["sha256"] == records["B"]["sha256"]:
            raise ValueError(f"{expected_public}: A/B byte-identical.")

    review = json.loads(review_path.read_text(encoding="utf-8"))
    if review.get("schema_version") != 1 or review.get("record_type") != "denoise_integrated_treatment_human_review":
        raise ValueError("Public review template schema/record_type inválido.")
    if review.get("phase") != "3.6k" or review.get("status") != "PENDING_HUMAN_REVIEW":
        raise ValueError("Public review template no está PENDING Phase 3.6k.")
    if str(review.get("reviewer") or ""):
        raise ValueError("Public review template no puede atribuir reviewer antes de escucha.")
    if review.get("precommit_sha256") != precommit_sha or review.get("bundle_manifest_sha256") != manifest_sha:
        raise ValueError("Public review template stale contra precommit/manifest.")
    decisions = review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 10:
        raise ValueError("Public review template debe contener 10 decisiones.")
    for index, decision in enumerate(decisions, start=1):
        if decision.get("case_id") != f"case_{index:02d}":
            raise ValueError("Public review template case labels incorrectos.")
        if decision.get("preference") != "PENDING" or decision.get("reason") != "":
            raise ValueError("Public review template contiene decisión humana prematura.")
        for label in ("A", "B"):
            if decision.get(label) != {"speech_integrity": "PENDING", "artifact": "PENDING"}:
                raise ValueError("Public review template contiene calidad humana prematura.")

    wav_files = sorted(PUBLIC_BUNDLE.rglob("*.wav"))
    if len(wav_files) != 30:
        raise ValueError(f"Public bundle WAV count {len(wav_files)} != 30.")

    print("PHASE3_6K_INDEPENDENT_TECHNICAL_EVIDENCE=PASS")
    print("PHASE3_6K_PUBLIC_MANIFEST_SHA=PASS")
    print("PHASE3_6K_PUBLIC_WAV_HASHES=30/30")
    print("PHASE3_6K_PUBLIC_AB_FRAME_MATCH=10/10")
    print("PHASE3_6K_PUBLIC_BLINDING_LEAKS=0")
    print("PHASE3_6K_HUMAN_REVIEW_STATUS=PENDING_HUMAN_REVIEW")
    print("PHASE3_6K_BUNDLE_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
