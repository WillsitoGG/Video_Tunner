from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .approval import evidence_fingerprint
from .denoise_runtime import SELECTED_DENOISER_ID, selected_denoiser_contract


DENOISE_PLAN_SCHEMA_VERSION = 1
DENOISE_PLAN_RECORD_TYPE = "denoise_plan_proposal"
DENOISE_PLAN_POLICY_ID = "deepfilternet_compensated_offline_fail_closed_v1"


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _normalise_sha(value: str, *, label: str) -> str:
    digest = str(value or "").strip().lower()
    if not _valid_sha256(digest):
        raise ValueError(f"{label} debe ser un SHA-256 válido.")
    return digest


def _validate_noise_evidence(
    noise_audit: dict[str, Any],
    *,
    noise_audit_sha256: str,
    current_output_sha256: str,
) -> dict[str, Any]:
    audit_digest = _normalise_sha(noise_audit_sha256, label="noise_audit_sha256")
    output_digest = _normalise_sha(current_output_sha256, label="current_output_sha256")
    if not isinstance(noise_audit, dict):
        raise ValueError("Noise audit debe ser un objeto JSON.")
    if noise_audit.get("schema_version") != 1 or noise_audit.get("record_type") != "noise_evidence_audit":
        raise ValueError("Denoise plan requiere noise_evidence_audit schema v1.")
    if noise_audit.get("valid") is not True:
        raise ValueError("Noise audit upstream no es válido.")

    quality_binding = noise_audit.get("quality_binding")
    if not isinstance(quality_binding, dict):
        raise ValueError("Noise audit sin quality_binding.")
    if quality_binding.get("required_quality_status") != "quality_audit_complete":
        raise ValueError("Noise audit no conserva quality_audit_complete.")
    quality_sha = _normalise_sha(
        str(quality_binding.get("quality_audit_sha256") or ""),
        label="quality_binding.quality_audit_sha256",
    )
    bound_output_sha = _normalise_sha(
        str(quality_binding.get("output_sha256") or ""),
        label="quality_binding.output_sha256",
    )
    if bound_output_sha != output_digest:
        raise ValueError("El output SHA actual no coincide con el output acreditado por noise audit; evidence stale.")

    treatment_policy = noise_audit.get("treatment_policy")
    if not isinstance(treatment_policy, dict):
        raise ValueError("Noise audit sin treatment_policy.")
    forbidden_policy_true = (
        "denoise_evaluated",
        "denoise_authorized",
        "filter_selected",
        "parameters_defined",
        "normalization_authorized",
        "join_smoothing_authorized",
    )
    if any(bool(treatment_policy.get(key)) for key in forbidden_policy_true):
        raise ValueError("Noise audit upstream contiene capability de tratamiento prohibida.")
    if noise_audit.get("executable") or noise_audit.get("treatment_authorized") or noise_audit.get("auto_apply"):
        raise ValueError("Noise audit upstream contiene capability ejecutable prohibida.")

    sufficient = bool(noise_audit.get("evidence_sufficient"))
    expected_status = "noise_measurement_complete" if sufficient else "insufficient_noise_evidence"
    if noise_audit.get("status") != expected_status:
        raise ValueError("Noise audit status/evidence_sufficient inconsistente.")

    return {
        "noise_audit_sha256": audit_digest,
        "noise_evidence_fingerprint": evidence_fingerprint(noise_audit),
        "quality_audit_sha256": quality_sha,
        "output_sha256": bound_output_sha,
        "evidence_sufficient": sufficient,
        "noise_status": expected_status,
    }


def _validate_selection_review(
    selection_review: dict[str, Any],
    *,
    selection_review_sha256: str,
) -> dict[str, Any]:
    digest = _normalise_sha(selection_review_sha256, label="selection_review_sha256")
    if not isinstance(selection_review, dict):
        raise ValueError("Selection review debe ser un objeto JSON.")
    if selection_review.get("schema_version") != 1 or selection_review.get("record_type") != "denoiser_selection_review":
        raise ValueError("Denoise plan requiere denoiser_selection_review schema v1.")
    if selection_review.get("phase") != "3.6f":
        raise ValueError("Selection review no corresponde a Phase 3.6f.")
    if selection_review.get("status") != "SELECTED_FOR_INTEGRATION_REVIEW" or selection_review.get("selection_completed") is not True:
        raise ValueError("Selection review no contiene una selección final para integration review.")
    if selection_review.get("selected_candidate_id") != SELECTED_DENOISER_ID:
        raise ValueError("Selection review no selecciona el candidato DeepFilterNet congelado.")

    eligible = selection_review.get("selection_eligible_candidates")
    if not isinstance(eligible, list) or SELECTED_DENOISER_ID not in eligible:
        raise ValueError("El candidato seleccionado no figura como selection_eligible.")
    evaluations = selection_review.get("candidate_evaluations")
    if not isinstance(evaluations, list):
        raise ValueError("Selection review sin candidate_evaluations.")
    matches = [item for item in evaluations if isinstance(item, dict) and item.get("candidate_id") == SELECTED_DENOISER_ID]
    if len(matches) != 1 or matches[0].get("selection_eligible") is not True or matches[0].get("objective_aggregate_gate_pass") is not True:
        raise ValueError("La evaluación del candidato seleccionado ya no es elegible.")

    interpretation = selection_review.get("interpretation")
    if not isinstance(interpretation, dict):
        raise ValueError("Selection review sin interpretation.")
    if interpretation.get("selected_candidate_is_for_integration_review_only") is not True:
        raise ValueError("Selection review no conserva integration-review-only.")
    if interpretation.get("candidate_selection_review_complete") is not True:
        raise ValueError("Selection review no está completa.")
    if interpretation.get("product_default") != "preserve" or interpretation.get("product_default_changed") is not False:
        raise ValueError("Selection review altera el product default conservador.")
    for key in ("denoise_authorized", "renderer_authorized", "auto_apply"):
        if interpretation.get(key) is not False:
            raise ValueError(f"Selection review contiene capability prohibida: {key}.")

    return {
        "selection_review_sha256": digest,
        "selection_review_fingerprint": evidence_fingerprint(selection_review),
        "candidate_id": SELECTED_DENOISER_ID,
        "selection_status": str(selection_review.get("status")),
    }


def _runtime_snapshot() -> dict[str, Any]:
    contract = selected_denoiser_contract()
    if contract.get("candidate_id") != SELECTED_DENOISER_ID:
        raise ValueError("Runtime contract no coincide con el candidato seleccionado.")
    state = contract.get("integration_state")
    media = contract.get("media_contract")
    if not isinstance(state, dict) or not isinstance(media, dict):
        raise ValueError("Runtime contract incompleto.")
    if state.get("selected_for_integration_review_only") is not True:
        raise ValueError("Runtime contract no conserva integration-review-only.")
    if state.get("runtime_download_allowed") is not False or state.get("product_default") != "preserve":
        raise ValueError("Runtime contract viola portable/preserve policy.")
    for key in ("denoise_authorized", "renderer_authorized", "auto_apply"):
        if state.get(key) is not False:
            raise ValueError(f"Runtime contract contiene capability prohibida: {key}.")
    if contract.get("arguments") != ["--compensate-delay", "--output-dir", "<output_dir>", "<input_wav>"]:
        raise ValueError("Runtime CLI ya no coincide con el contrato 3.6g.")
    if media.get("input_pcm") != "pcm_s16le" or media.get("input_channels") != 1 or media.get("input_sample_rate_hz") != 48000:
        raise ValueError("Runtime input media contract cambió respecto a 3.6g.")
    if media.get("output_channels") != 1 or media.get("output_sample_rate_hz") != 48000:
        raise ValueError("Runtime output media contract cambió respecto a 3.6g.")
    if float(media.get("raw_duration_delta_max_seconds")) != 0.05:
        raise ValueError("Runtime temporal contract cambió respecto a 3.6g.")
    return {
        "contract": contract,
        "contract_fingerprint": evidence_fingerprint(contract),
    }


def build_denoise_plan_proposal(
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    current_output_sha256: str,
) -> dict[str, Any]:
    """Prepare a non-executable denoise proposal for explicit authorization review.

    `evidence_sufficient` is used only as a measurement-coverage guard. It is not
    interpreted as evidence that denoise is needed. No process is launched and
    this proposal never grants execution capability.
    """
    noise = _validate_noise_evidence(
        noise_audit,
        noise_audit_sha256=noise_audit_sha256,
        current_output_sha256=current_output_sha256,
    )
    selection = _validate_selection_review(
        selection_review,
        selection_review_sha256=selection_review_sha256,
    )
    runtime = _runtime_snapshot()

    blockers: list[dict[str, Any]] = []
    if not noise["evidence_sufficient"]:
        blockers.append(
            {
                "code": "insufficient_noise_measurement_coverage",
                "meaning": "More reliable non-speech coverage is required before preparing treatment parameters; this is not evidence that denoise is needed.",
            }
        )

    ready = not blockers
    contract = runtime["contract"]
    media = contract["media_contract"]
    return {
        "schema_version": DENOISE_PLAN_SCHEMA_VERSION,
        "record_type": DENOISE_PLAN_RECORD_TYPE,
        "status": "denoise_plan_proposal_ready" if ready else "denoise_plan_blocked",
        "ready_for_execution_authorization": ready,
        "bindings": {
            "noise_audit_sha256": noise["noise_audit_sha256"],
            "noise_evidence_fingerprint": noise["noise_evidence_fingerprint"],
            "quality_audit_sha256": noise["quality_audit_sha256"],
            "quality_output_sha256": noise["output_sha256"],
            "selection_review_sha256": selection["selection_review_sha256"],
            "selection_review_fingerprint": selection["selection_review_fingerprint"],
            "selected_candidate_id": selection["candidate_id"],
            "runtime_contract_fingerprint": runtime["contract_fingerprint"],
        },
        "policy": {
            "policy_id": DENOISE_PLAN_POLICY_ID,
            "mode": "selected_deepfilternet_offline_fail_closed",
            "noise_evidence_role": "measurement_coverage_only_not_treatment_trigger",
            "explicit_execution_authorization_required": True,
            "runtime_download_allowed": False,
            "network_access_required": False,
            "source_overwrite_allowed": False,
            "product_default": "preserve",
        },
        "runtime": {
            "candidate_id": contract["candidate_id"],
            "implementation": contract["implementation"],
            "version": contract["version"],
            "asset_sha256": contract["asset_sha256"],
            "asset_size_bytes": contract["asset_size_bytes"],
            "runtime_relative_path": contract["runtime_relative_path"],
            "arguments_template": list(contract["arguments"]),
            "explicit_model_argument": contract["explicit_model_argument"],
        },
        "media_contract": {
            "input_pcm": media["input_pcm"],
            "input_channels": media["input_channels"],
            "input_sample_rate_hz": media["input_sample_rate_hz"],
            "output_channels": media["output_channels"],
            "output_sample_rate_hz": media["output_sample_rate_hz"],
            "raw_duration_delta_max_seconds": media["raw_duration_delta_max_seconds"],
            "delay_compensation_required": True,
        },
        "blockers": blockers,
        "parameters_defined": ready,
        "parameters_executable": False,
        "denoise_authorized": False,
        "denoise_render_authorization": False,
        "plan_render_authorization": False,
        "renderer_available": False,
        "executable": False,
        "auto_apply": False,
    }


def validate_denoise_plan_proposal(
    noise_audit: dict[str, Any],
    selection_review: dict[str, Any],
    plan: dict[str, Any],
    *,
    noise_audit_sha256: str,
    selection_review_sha256: str,
    current_output_sha256: str,
) -> dict[str, Any]:
    """Rebuild and compare the exact 3.6h proposal against current evidence."""
    base = {
        "valid": False,
        "ready": False,
        "parameters_executable": False,
        "denoise_render_authorization": False,
        "plan_render_authorization": False,
        "renderer_available": False,
        "executable": False,
        "auto_apply": False,
    }
    if not isinstance(plan, dict):
        return base | {"status": "invalid_record", "reason": "plan_not_object"}
    if plan.get("schema_version") != DENOISE_PLAN_SCHEMA_VERSION:
        return base | {"status": "invalid_record", "reason": "unsupported_schema_version"}
    if plan.get("record_type") != DENOISE_PLAN_RECORD_TYPE:
        return base | {"status": "invalid_record", "reason": "invalid_record_type"}
    forbidden_true = (
        "parameters_executable",
        "denoise_authorized",
        "denoise_render_authorization",
        "plan_render_authorization",
        "renderer_available",
        "executable",
        "auto_apply",
    )
    if any(bool(plan.get(key)) for key in forbidden_true):
        return base | {"status": "invalid_record", "reason": "unexpected_execution_capability"}

    try:
        expected = build_denoise_plan_proposal(
            noise_audit,
            selection_review,
            noise_audit_sha256=noise_audit_sha256,
            selection_review_sha256=selection_review_sha256,
            current_output_sha256=current_output_sha256,
        )
    except (ValueError, TypeError) as exc:
        return base | {"status": "stale_or_invalid_upstream", "reason": str(exc)}
    if plan != expected:
        return base | {"status": "stale_or_tampered_plan", "reason": "plan_no_longer_matches_exact_upstream_rebuild"}

    ready = (
        expected.get("status") == "denoise_plan_proposal_ready"
        and bool(expected.get("ready_for_execution_authorization"))
        and expected.get("blockers") in ([], None)
        and bool(expected.get("parameters_defined"))
    )
    if not ready:
        return base | {
            "status": "valid_blocked",
            "reason": "plan_not_ready_for_execution_authorization",
            "valid": True,
        }
    return base | {
        "status": "valid_ready",
        "reason": None,
        "valid": True,
        "ready": True,
        "quality_output_sha256": expected["bindings"]["quality_output_sha256"],
        "selected_candidate_id": expected["bindings"]["selected_candidate_id"],
        "runtime_contract_fingerprint": expected["bindings"]["runtime_contract_fingerprint"],
    }


def save_denoise_plan_proposal(record: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
