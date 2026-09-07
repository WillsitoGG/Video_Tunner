from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


REVIEW_SCHEMA_VERSION = 1
REVIEW_RECORD_TYPE = "denoiser_human_perceptual_review"
GATE_RECORD_TYPE = "denoiser_human_perceptual_gate"
PENDING = "PENDING"


def sha256_path(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_pending_review_template(*, policy: dict[str, Any], policy_sha256: str, bundle_manifest_sha256: str) -> dict[str, Any]:
    decisions = []
    selected = policy["case_selection"]["cases_in_selection_rank_order"]
    for case in selected:
        for pair in policy["pairwise_comparisons"]:
            decisions.append(
                {
                    "case_id": case["id"],
                    "comparison": pair["public_pair_label"],
                    "preference": PENDING,
                    "A": {"speech_integrity": PENDING, "artifact": PENDING},
                    "B": {"speech_integrity": PENDING, "artifact": PENDING},
                    "reason": "",
                }
            )
    return {
        "schema_version": REVIEW_SCHEMA_VERSION,
        "record_type": REVIEW_RECORD_TYPE,
        "policy_id": policy["policy_id"],
        "policy_sha256": policy_sha256,
        "bundle_manifest_sha256": bundle_manifest_sha256,
        "reviewer": "",
        "status": "PENDING_HUMAN_REVIEW",
        "decisions": decisions,
        "capabilities": {
            "candidate_selection_authorized": False,
            "denoiser_selected": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }


def _expected_decision_keys(policy: dict[str, Any]) -> set[tuple[str, str]]:
    case_ids = [case["id"] for case in policy["case_selection"]["cases_in_selection_rank_order"]]
    comparisons = [pair["public_pair_label"] for pair in policy["pairwise_comparisons"]]
    return {(case_id, comparison) for case_id in case_ids for comparison in comparisons}


def remap_public_review_to_private(*, public_review: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    """Convert the blinded public case labels back to the frozen private ids.

    Only case_id values are remapped. Preferences, A/B quality judgments and
    reasons are copied verbatim. Unknown/duplicate public labels fail closed.
    """
    selected = policy["case_selection"]["cases_in_selection_rank_order"]
    public_to_private = {f"case_{index:02d}": case["id"] for index, case in enumerate(selected, start=1)}
    allowed_comparisons = {pair["public_pair_label"] for pair in policy["pairwise_comparisons"]}
    expected_public = {
        (public_case, comparison)
        for public_case in public_to_private
        for comparison in allowed_comparisons
    }

    decisions = public_review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(expected_public):
        raise ValueError("Public human denoiser review no contiene exactamente las decisiones ciegas esperadas.")

    seen: set[tuple[str, str]] = set()
    remapped: list[dict[str, Any]] = []
    for decision in decisions:
        public_case = decision.get("case_id")
        comparison = decision.get("comparison")
        key = (public_case, comparison)
        if key not in expected_public or key in seen:
            raise ValueError(f"Public human denoiser review contiene decisión desconocida/duplicada: {key!r}")
        seen.add(key)
        copied = dict(decision)
        copied["case_id"] = public_to_private[public_case]
        remapped.append(copied)
    if seen != expected_public:
        raise ValueError("Public human denoiser review no cubre exactamente el bundle ciego congelado.")

    private_review = dict(public_review)
    private_review["decisions"] = remapped
    private_review.pop("note", None)
    return private_review


def validate_completed_review(
    *,
    review: dict[str, Any],
    policy: dict[str, Any],
    expected_policy_sha256: str,
    expected_bundle_manifest_sha256: str,
) -> None:
    if review.get("schema_version") != REVIEW_SCHEMA_VERSION or review.get("record_type") != REVIEW_RECORD_TYPE:
        raise ValueError("Human denoiser review schema/record_type inválido.")
    if review.get("policy_id") != policy.get("policy_id"):
        raise ValueError("Human denoiser review policy_id no coincide.")
    if review.get("policy_sha256") != expected_policy_sha256:
        raise ValueError("Human denoiser review policy SHA no coincide.")
    if review.get("bundle_manifest_sha256") != expected_bundle_manifest_sha256:
        raise ValueError("Human denoiser review bundle manifest SHA no coincide.")
    reviewer = str(review.get("reviewer", "")).strip()
    if not reviewer:
        raise ValueError("Human denoiser review requiere reviewer no vacío.")
    if review.get("status") != "COMPLETE":
        raise ValueError("Human denoiser review debe marcar status=COMPLETE.")

    expected = _expected_decision_keys(policy)
    decisions = review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(expected):
        raise ValueError("Human denoiser review no contiene exactamente las decisiones precomprometidas.")

    seen: set[tuple[str, str]] = set()
    allowed_preferences = set(policy["review_form"]["preference_values"])
    allowed_binary = set(policy["review_form"]["per_clip_speech_integrity_values"])
    allowed_artifact = set(policy["review_form"]["per_clip_artifact_values"])
    for decision in decisions:
        key = (decision.get("case_id"), decision.get("comparison"))
        if key not in expected or key in seen:
            raise ValueError(f"Human denoiser review contiene decisión desconocida/duplicada: {key!r}")
        seen.add(key)
        if decision.get("preference") not in allowed_preferences:
            raise ValueError(f"{key}: preference inválida.")
        for label in ("A", "B"):
            clip = decision.get(label)
            if not isinstance(clip, dict):
                raise ValueError(f"{key}: falta evaluación de {label}.")
            if clip.get("speech_integrity") not in allowed_binary:
                raise ValueError(f"{key}: speech_integrity inválido para {label}.")
            if clip.get("artifact") not in allowed_artifact:
                raise ValueError(f"{key}: artifact inválido para {label}.")
        if not str(decision.get("reason", "")).strip():
            raise ValueError(f"{key}: reason obligatorio.")
    if seen != expected:
        raise ValueError("Human denoiser review no cubre exactamente el corpus perceptual congelado.")

    caps = review.get("capabilities")
    expected_caps = {
        "candidate_selection_authorized": False,
        "denoiser_selected": False,
        "denoise_authorized": False,
        "renderer_authorized": False,
        "auto_apply": False,
    }
    if caps != expected_caps:
        raise ValueError("Human denoiser review capability fields han sido alterados.")


def build_perceptual_gate(
    *,
    review: dict[str, Any],
    policy: dict[str, Any],
    expected_policy_sha256: str,
    expected_bundle_manifest_sha256: str,
) -> dict[str, Any]:
    validate_completed_review(
        review=review,
        policy=policy,
        expected_policy_sha256=expected_policy_sha256,
        expected_bundle_manifest_sha256=expected_bundle_manifest_sha256,
    )
    decision_by_key = {(item["case_id"], item["comparison"]): item for item in review["decisions"]}
    gate_policy = policy["per_treatment_advancement_gate"]
    pair_results = []

    for pair in policy["pairwise_comparisons"]:
        comparison = pair["public_pair_label"]
        treatment_labels = pair["treatment_label_by_case"]
        treatment_preferences = 0
        preserve_preferences = 0
        no_preferences = 0
        treatment_speech_failures = 0
        treatment_artifact_failures = 0
        cases = []

        for case in policy["case_selection"]["cases_in_selection_rank_order"]:
            case_id = case["id"]
            decision = decision_by_key[(case_id, comparison)]
            treatment_label = treatment_labels[case_id]
            preserve_label = "B" if treatment_label == "A" else "A"
            preference = decision["preference"]
            if preference == treatment_label:
                treatment_preferences += 1
                preference_class = "TREATMENT"
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
            cases.append(
                {
                    "case_id": case_id,
                    "preference_class": preference_class,
                    "treatment_speech_integrity": treatment_clip["speech_integrity"],
                    "treatment_artifact": treatment_clip["artifact"],
                    "reason": decision["reason"],
                }
            )

        if treatment_preferences + preserve_preferences + no_preferences != gate_policy["required_reviews"]:
            raise ValueError("Perceptual gate review count interno inconsistente.")
        passed = (
            treatment_preferences >= gate_policy["minimum_treatment_preferences"]
            and treatment_speech_failures <= gate_policy["maximum_treatment_speech_integrity_failures"]
            and treatment_artifact_failures <= gate_policy["maximum_treatment_artifact_failures"]
        )
        pair_results.append(
            {
                "pair_id": pair["pair_id"],
                "public_pair_label": comparison,
                "treatment_candidate_id": pair["treatment_candidate_id"],
                "control_candidate_id": pair["control_candidate_id"],
                "review_count": gate_policy["required_reviews"],
                "treatment_preferences": treatment_preferences,
                "preserve_preferences": preserve_preferences,
                "no_preference": no_preferences,
                "treatment_speech_integrity_failures": treatment_speech_failures,
                "treatment_artifact_failures": treatment_artifact_failures,
                "perceptual_gate_pass": passed,
                "status": "ELIGIBLE_FOR_SELECTION_REVIEW" if passed else "NOT_ADVANCED_PRESERVE_DEFAULT",
                "cases": cases,
            }
        )

    return {
        "schema_version": 1,
        "record_type": GATE_RECORD_TYPE,
        "policy_id": policy["policy_id"],
        "policy_sha256": expected_policy_sha256,
        "bundle_manifest_sha256": expected_bundle_manifest_sha256,
        "review_fingerprint": hashlib.sha256(
            json.dumps(review, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "pair_results": pair_results,
        "interpretation": {
            "human_perceptual_evidence_complete": True,
            "gate_pass_only_means_eligible_for_later_candidate_selection_review": True,
            "candidate_selection_authorized": False,
            "denoiser_selected": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
            "preserve_remains_product_default": True,
        },
    }
