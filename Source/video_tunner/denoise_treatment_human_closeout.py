from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .approval import evidence_fingerprint


REVIEW_SCHEMA_VERSION = 1
REVIEW_RECORD_TYPE = "denoise_integrated_treatment_human_review"
TECHNICAL_EVIDENCE_SCHEMA_VERSION = 1
TECHNICAL_EVIDENCE_RECORD_TYPE = "phase3_denoise_treatment_human_bundle_technical_evidence"
CLOSEOUT_SCHEMA_VERSION = 1
CLOSEOUT_RECORD_TYPE = "phase3_denoise_treatment_human_closeout"
PENDING = "PENDING"


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _normalise_sha(value: str, *, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not _valid_sha256(digest):
        raise ValueError(f"{label} debe ser un SHA-256 válido.")
    return digest


def _required_cases(precommit: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(precommit, dict):
        raise ValueError("Phase 3.6k precommit debe ser un objeto JSON.")
    if precommit.get("schema_version") != 1:
        raise ValueError("Phase 3.6k precommit schema no soportado.")
    if precommit.get("record_type") != "phase3_denoise_treatment_human_closeout_precommit":
        raise ValueError("Phase 3.6k precommit record_type inválido.")
    if precommit.get("phase") != "3.6k":
        raise ValueError("Precommit no corresponde a Phase 3.6k.")
    if precommit.get("status") != "PRECOMMITTED_BEFORE_INTEGRATED_LISTENING_BUNDLE":
        raise ValueError("Phase 3.6k precommit no está congelado antes del bundle.")
    selection = precommit.get("case_selection")
    if not isinstance(selection, dict):
        raise ValueError("Phase 3.6k precommit sin case_selection.")
    cases = selection.get("cases_in_required_order")
    if not isinstance(cases, list) or len(cases) != 10:
        raise ValueError("Phase 3.6k requiere exactamente 10 casos congelados.")
    ids = [str(case.get("id") or "") for case in cases if isinstance(case, dict)]
    if len(ids) != 10 or any(not value for value in ids) or len(set(ids)) != 10:
        raise ValueError("Phase 3.6k case ids inválidos o duplicados.")
    return cases


def _public_case_mapping(precommit: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    cases = _required_cases(precommit)
    private_to_public = {case["id"]: f"case_{index:02d}" for index, case in enumerate(cases, start=1)}
    public_to_private = {public: private for private, public in private_to_public.items()}
    return private_to_public, public_to_private


def build_pending_integrated_review_template(
    *,
    precommit: dict[str, Any],
    precommit_sha256: str,
    bundle_manifest_sha256: str,
) -> dict[str, Any]:
    precommit_sha = _normalise_sha(precommit_sha256, label="precommit_sha256")
    manifest_sha = _normalise_sha(bundle_manifest_sha256, label="bundle_manifest_sha256")
    cases = _required_cases(precommit)
    decisions = [
        {
            "case_id": case["id"],
            "preference": PENDING,
            "A": {"speech_integrity": PENDING, "artifact": PENDING},
            "B": {"speech_integrity": PENDING, "artifact": PENDING},
            "reason": "",
        }
        for case in cases
    ]
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "record_type": REVIEW_RECORD_TYPE,
        "phase": "3.6k",
        "precommit_sha256": precommit_sha,
        "bundle_manifest_sha256": manifest_sha,
        "reviewer": "",
        "status": "PENDING_HUMAN_REVIEW",
        "decisions": decisions,
        "capabilities": {
            "real_guille_authorization_created": False,
            "product_default_changed": False,
            "auto_apply": False,
            "stereo_or_multichannel_generalized": False,
        },
    }


def remap_public_integrated_review_to_private(
    *,
    public_review: dict[str, Any],
    precommit: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(public_review, dict):
        raise ValueError("Public Phase 3.6k review debe ser un objeto JSON.")
    _, public_to_private = _public_case_mapping(precommit)
    decisions = public_review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 10:
        raise ValueError("Public Phase 3.6k review no contiene exactamente 10 decisiones.")
    seen: set[str] = set()
    remapped: list[dict[str, Any]] = []
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("Cada decisión pública 3.6k debe ser un objeto.")
        public_case = str(decision.get("case_id") or "")
        if public_case not in public_to_private or public_case in seen:
            raise ValueError(f"Public Phase 3.6k review contiene case desconocido/duplicado: {public_case!r}")
        seen.add(public_case)
        copied = dict(decision)
        copied["case_id"] = public_to_private[public_case]
        remapped.append(copied)
    if seen != set(public_to_private):
        raise ValueError("Public Phase 3.6k review no cubre exactamente el bundle congelado.")
    private = dict(public_review)
    private["decisions"] = remapped
    private.pop("note", None)
    return private


def validate_integrated_bundle_technical_evidence(
    *,
    technical_evidence: dict[str, Any],
    precommit: dict[str, Any],
    expected_precommit_sha256: str,
) -> dict[str, Any]:
    expected_precommit_sha = _normalise_sha(expected_precommit_sha256, label="expected_precommit_sha256")
    cases = _required_cases(precommit)
    expected_ids = [case["id"] for case in cases]
    blind = precommit.get("blinding_contract")
    if not isinstance(blind, dict):
        raise ValueError("Phase 3.6k precommit sin blinding_contract.")
    expected_labels = blind.get("treatment_label_by_case")
    if not isinstance(expected_labels, dict) or set(expected_labels) != set(expected_ids):
        raise ValueError("Phase 3.6k precommit blinding mapping inválido.")

    if not isinstance(technical_evidence, dict):
        raise ValueError("Phase 3.6k technical evidence debe ser objeto JSON.")
    if technical_evidence.get("schema_version") != TECHNICAL_EVIDENCE_SCHEMA_VERSION:
        raise ValueError("Phase 3.6k technical evidence schema no soportado.")
    if technical_evidence.get("record_type") != TECHNICAL_EVIDENCE_RECORD_TYPE:
        raise ValueError("Phase 3.6k technical evidence record_type inválido.")
    if technical_evidence.get("phase") != "3.6k":
        raise ValueError("Technical evidence no corresponde a Phase 3.6k.")
    if technical_evidence.get("status") != "TECHNICAL_BUNDLE_READY_FOR_HUMAN_REVIEW":
        raise ValueError("Technical evidence no acredita bundle listo para review humano.")
    if technical_evidence.get("precommit_sha256") != expected_precommit_sha:
        raise ValueError("Technical evidence precommit SHA no coincide.")
    manifest_sha = _normalise_sha(
        str(technical_evidence.get("public_bundle_manifest_sha256") or ""),
        label="public_bundle_manifest_sha256",
    )
    if technical_evidence.get("case_count") != 10 or technical_evidence.get("technical_pass_count") != 10:
        raise ValueError("Technical evidence no acredita 10/10 technical PASS.")
    if technical_evidence.get("invalid_or_stale_count") != 0 or technical_evidence.get("technical_fail_count") != 0:
        raise ValueError("Technical evidence contiene fail/stale y no puede habilitar escucha.")

    entries = technical_evidence.get("cases")
    if not isinstance(entries, list) or len(entries) != 10:
        raise ValueError("Technical evidence debe contener exactamente 10 casos.")
    seen: set[str] = set()
    private_to_public, _ = _public_case_mapping(precommit)
    by_case: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Technical evidence case no es objeto.")
        case_id = str(entry.get("case_id") or "")
        if case_id not in expected_ids or case_id in seen:
            raise ValueError(f"Technical evidence case desconocido/duplicado: {case_id!r}")
        seen.add(case_id)
        if entry.get("public_case") != private_to_public[case_id]:
            raise ValueError(f"{case_id}: public_case no coincide con orden congelado.")
        if entry.get("treatment_label") != expected_labels[case_id]:
            raise ValueError(f"{case_id}: treatment label no coincide con blinding precommit.")

        verification = entry.get("technical_verification")
        if not isinstance(verification, dict):
            raise ValueError(f"{case_id}: falta technical_verification snapshot.")
        if verification.get("record_type") != "denoise_post_render_verification":
            raise ValueError(f"{case_id}: technical verification type inválido.")
        if verification.get("status") != "technical_denoise_pass" or verification.get("technical_pass") is not True:
            raise ValueError(f"{case_id}: technical verification no es PASS.")
        if verification.get("valid_evidence") is not True:
            raise ValueError(f"{case_id}: technical verification no acredita evidence válida.")
        if verification.get("blockers") not in ([], None):
            raise ValueError(f"{case_id}: technical verification contiene blockers.")
        if verification.get("human_perceptual_review_required") is not True or verification.get("human_pass") is not False:
            raise ValueError(f"{case_id}: technical verification confunde technical y human PASS.")
        if verification.get("product_default") != "preserve" or verification.get("auto_apply") is not False:
            raise ValueError(f"{case_id}: technical verification altera preserve/auto_apply.")
        if verification.get("decoded_video_equal") is not True:
            raise ValueError(f"{case_id}: decoded video no es idéntico.")
        if int(verification.get("source_frames", -1)) <= 0:
            raise ValueError(f"{case_id}: source frame count inválido.")
        if verification.get("source_frames") != verification.get("output_frames"):
            raise ValueError(f"{case_id}: decoded audio frame count no coincide.")

        for sha_key in (
            "technical_verification_sha256",
            "source_media_sha256",
            "rendered_media_sha256",
            "preserve_wav_sha256",
            "treatment_wav_sha256",
            "clean_reference_wav_sha256",
            "A_wav_sha256",
            "B_wav_sha256",
        ):
            _normalise_sha(str(entry.get(sha_key) or ""), label=f"{case_id}.{sha_key}")
        if entry["A_wav_sha256"] == entry["B_wav_sha256"]:
            raise ValueError(f"{case_id}: A y B son bytes idénticos; bundle no discrimina tratamiento/preserve.")
        treatment_sha = entry["A_wav_sha256"] if entry["treatment_label"] == "A" else entry["B_wav_sha256"]
        preserve_sha = entry["B_wav_sha256"] if entry["treatment_label"] == "A" else entry["A_wav_sha256"]
        if treatment_sha != entry["treatment_wav_sha256"]:
            raise ValueError(f"{case_id}: treatment public SHA no coincide con treatment decoded SHA.")
        if preserve_sha != entry["preserve_wav_sha256"]:
            raise ValueError(f"{case_id}: preserve public SHA no coincide con preserve decoded SHA.")
        by_case[case_id] = entry

    if seen != set(expected_ids):
        raise ValueError("Technical evidence no cubre exactamente los 10 casos congelados.")

    caps = technical_evidence.get("capabilities")
    expected_caps = {
        "real_guille_authorization_created": False,
        "real_guille_media_processed": False,
        "product_default": "preserve",
        "auto_apply": False,
        "stereo_or_multichannel_generalized": False,
    }
    if caps != expected_caps:
        raise ValueError("Technical evidence capability fields han sido alterados.")

    return {
        "valid": True,
        "status": "technical_bundle_valid",
        "public_bundle_manifest_sha256": manifest_sha,
        "case_count": 10,
        "technical_pass_count": 10,
        "cases": by_case,
    }


def validate_completed_integrated_review(
    *,
    review: dict[str, Any],
    precommit: dict[str, Any],
    expected_precommit_sha256: str,
    expected_bundle_manifest_sha256: str,
) -> None:
    precommit_sha = _normalise_sha(expected_precommit_sha256, label="expected_precommit_sha256")
    manifest_sha = _normalise_sha(expected_bundle_manifest_sha256, label="expected_bundle_manifest_sha256")
    cases = _required_cases(precommit)
    expected_ids = [case["id"] for case in cases]
    if not isinstance(review, dict):
        raise ValueError("Phase 3.6k human review debe ser objeto JSON.")
    if review.get("schema_version") != REVIEW_SCHEMA_VERSION or review.get("record_type") != REVIEW_RECORD_TYPE:
        raise ValueError("Phase 3.6k human review schema/record_type inválido.")
    if review.get("phase") != "3.6k":
        raise ValueError("Human review no corresponde a Phase 3.6k.")
    if review.get("precommit_sha256") != precommit_sha:
        raise ValueError("Human review precommit SHA no coincide.")
    if review.get("bundle_manifest_sha256") != manifest_sha:
        raise ValueError("Human review bundle manifest SHA no coincide.")
    if review.get("status") != "COMPLETE":
        raise ValueError("Human review debe marcar status=COMPLETE.")
    if not str(review.get("reviewer") or "").strip():
        raise ValueError("Human review requiere reviewer no vacío.")

    form = precommit.get("human_review_form")
    if not isinstance(form, dict):
        raise ValueError("Phase 3.6k precommit sin human_review_form.")
    allowed_preferences = set(form["preference_values"])
    allowed_integrity = set(form["per_clip_speech_integrity_values"])
    allowed_artifact = set(form["per_clip_artifact_values"])
    decisions = review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != 10:
        raise ValueError("Human review debe contener exactamente 10 decisiones.")
    seen: set[str] = set()
    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("Human review decision no es objeto.")
        case_id = str(decision.get("case_id") or "")
        if case_id not in expected_ids or case_id in seen:
            raise ValueError(f"Human review case desconocido/duplicado: {case_id!r}")
        seen.add(case_id)
        if decision.get("preference") not in allowed_preferences:
            raise ValueError(f"{case_id}: preference inválida.")
        for label in ("A", "B"):
            clip = decision.get(label)
            if not isinstance(clip, dict):
                raise ValueError(f"{case_id}: falta evaluación {label}.")
            if clip.get("speech_integrity") not in allowed_integrity:
                raise ValueError(f"{case_id}: speech_integrity inválido para {label}.")
            if clip.get("artifact") not in allowed_artifact:
                raise ValueError(f"{case_id}: artifact inválido para {label}.")
        if not str(decision.get("reason") or "").strip():
            raise ValueError(f"{case_id}: reason humano obligatorio.")
    if seen != set(expected_ids):
        raise ValueError("Human review no cubre exactamente los 10 casos congelados.")

    caps = review.get("capabilities")
    expected_caps = {
        "real_guille_authorization_created": False,
        "product_default_changed": False,
        "auto_apply": False,
        "stereo_or_multichannel_generalized": False,
    }
    if caps != expected_caps:
        raise ValueError("Human review capability fields han sido alterados.")


def build_integrated_treatment_human_closeout(
    *,
    review: dict[str, Any],
    technical_evidence: dict[str, Any],
    precommit: dict[str, Any],
    expected_precommit_sha256: str,
    technical_evidence_sha256: str,
) -> dict[str, Any]:
    technical_sha = _normalise_sha(technical_evidence_sha256, label="technical_evidence_sha256")
    technical = validate_integrated_bundle_technical_evidence(
        technical_evidence=technical_evidence,
        precommit=precommit,
        expected_precommit_sha256=expected_precommit_sha256,
    )
    validate_completed_integrated_review(
        review=review,
        precommit=precommit,
        expected_precommit_sha256=expected_precommit_sha256,
        expected_bundle_manifest_sha256=technical["public_bundle_manifest_sha256"],
    )

    decisions = {item["case_id"]: item for item in review["decisions"]}
    treatment_preferences = 0
    preserve_preferences = 0
    no_preferences = 0
    treatment_speech_failures = 0
    treatment_artifact_failures = 0
    case_results: list[dict[str, Any]] = []

    for case in _required_cases(precommit):
        case_id = case["id"]
        entry = technical["cases"][case_id]
        treatment_label = entry["treatment_label"]
        preserve_label = "B" if treatment_label == "A" else "A"
        decision = decisions[case_id]
        preference = decision["preference"]
        if preference == treatment_label:
            treatment_preferences += 1
            preference_class = "INTEGRATED_TREATMENT"
        elif preference == preserve_label:
            preserve_preferences += 1
            preference_class = "PRESERVE"
        else:
            no_preferences += 1
            preference_class = "NO_PREFERENCE"
        treatment_clip = decision[treatment_label]
        if treatment_clip["speech_integrity"] == "FAIL":
            treatment_speech_failures += 1
        if treatment_clip["artifact"] == "FAIL":
            treatment_artifact_failures += 1
        case_results.append(
            {
                "case_id": case_id,
                "public_case": entry["public_case"],
                "preference_class": preference_class,
                "integrated_treatment_speech_integrity": treatment_clip["speech_integrity"],
                "integrated_treatment_artifact": treatment_clip["artifact"],
                "reason": decision["reason"],
            }
        )

    gate = precommit["human_closeout_gate"]
    if treatment_preferences + preserve_preferences + no_preferences != gate["required_reviews"]:
        raise ValueError("Phase 3.6k review count interno inconsistente.")
    passed = (
        treatment_preferences >= gate["minimum_integrated_treatment_preferences"]
        and treatment_speech_failures <= gate["maximum_integrated_treatment_speech_integrity_failures"]
        and treatment_artifact_failures <= gate["maximum_integrated_treatment_artifact_failures"]
    )
    status = gate["pass_status"] if passed else gate["fail_status"]

    return {
        "schema_version": CLOSEOUT_SCHEMA_VERSION,
        "record_type": CLOSEOUT_RECORD_TYPE,
        "phase": "3.6k",
        "status": status,
        "precommit_sha256": str(expected_precommit_sha256).strip().lower(),
        "technical_evidence_sha256": technical_sha,
        "public_bundle_manifest_sha256": technical["public_bundle_manifest_sha256"],
        "review_fingerprint": evidence_fingerprint(review),
        "reviewer": review["reviewer"],
        "human_listening_completed": True,
        "results": {
            "required_reviews": gate["required_reviews"],
            "integrated_treatment_preferences": treatment_preferences,
            "preserve_preferences": preserve_preferences,
            "no_preference": no_preferences,
            "integrated_treatment_speech_integrity_failures": treatment_speech_failures,
            "integrated_treatment_artifact_failures": treatment_artifact_failures,
            "technical_pass_count": technical["technical_pass_count"],
            "human_gate_pass": passed,
            "cases": case_results,
        },
        "interpretation": {
            "integrated_mono_deepfilternet_human_closeout_ready": passed,
            "failure_keeps_phase_open": not passed,
            "thresholds_relaxed_post_hoc": False,
            "real_guille_authorization_created": False,
            "real_guille_media_authorized": False,
            "real_guille_media_processed": False,
            "product_default": "preserve",
            "auto_apply": False,
            "stereo_or_multichannel_generalized": False,
        },
    }


def save_json(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
