from __future__ import annotations

import math
from statistics import fmean
from typing import Any


SELECTION_RECORD_TYPE = "denoiser_selection_review"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _mean(values: list[float], *, label: str) -> float:
    _require(bool(values), f"{label}: no hay valores para calcular la media.")
    result = float(fmean(values))
    _require(math.isfinite(result), f"{label}: media no finita.")
    return result


def _close(a: float, b: float, *, tolerance: float = 1e-8) -> bool:
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=tolerance)


def _validate_bindings(*, objective: dict[str, Any], human_gate: dict[str, Any], policy: dict[str, Any]) -> None:
    bindings = policy["bindings"]

    _require(objective.get("record_type") == "denoiser_candidate_objective_comparison", "Evidencia objetiva record_type inválido.")
    _require(objective.get("status") == "objective_comparison_complete", "Evidencia objetiva incompleta.")
    _require(objective.get("valid") is True, "Evidencia objetiva no válida.")
    _require(objective.get("policy_id") == bindings["objective_comparison_policy_id"], "Policy objetiva no coincide con 3.6f.")
    provenance = objective.get("provenance") or {}
    _require(provenance.get("workflow_run_id") == bindings["objective_comparison_run_id"], "Run objetivo no coincide con 3.6f.")
    _require(provenance.get("raw_comparison_json_sha256") == bindings["objective_comparison_raw_json_sha256"], "SHA de evidencia objetiva no coincide con 3.6f.")

    _require(human_gate.get("record_type") == "denoiser_human_perceptual_gate", "Human gate record_type inválido.")
    _require(human_gate.get("policy_id") == bindings["human_policy_id"], "Human policy_id no coincide con 3.6f.")
    _require(human_gate.get("policy_sha256") == bindings["human_policy_sha256"], "Human policy SHA no coincide con 3.6f.")
    _require(human_gate.get("bundle_manifest_sha256") == bindings["bundle_manifest_sha256"], "Bundle manifest SHA no coincide con 3.6f.")
    _require(human_gate.get("review_fingerprint") == bindings["human_review_fingerprint"], "Human review fingerprint no coincide con 3.6f.")

    interpretation = human_gate.get("interpretation") or {}
    _require(interpretation.get("human_perceptual_evidence_complete") is True, "Human evidence no está completa.")
    for key in ("candidate_selection_authorized", "denoise_authorized", "renderer_authorized", "auto_apply"):
        _require(interpretation.get(key) is False, f"Human gate altera capability prohibida: {key}.")
    _require(interpretation.get("preserve_remains_product_default") is True, "Human gate no preserva el default conservador.")


def _validate_timeline(*, timeline: dict[str, Any], max_abs_delta: float, label: str) -> None:
    for key in ("alignment_search_performed", "time_shift_performed", "level_matching_performed"):
        _require(timeline.get(key) is False, f"{label}: timeline viola {key}.")
    raw_delta = float(timeline.get("raw_duration_delta_seconds", 0.0))
    _require(math.isfinite(raw_delta), f"{label}: raw_duration_delta_seconds no finito.")
    _require(abs(raw_delta) <= max_abs_delta + 1e-12, f"{label}: delta temporal supera el máximo precomprometido.")


def _evaluate_candidate(*, candidate_id: str, objective: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    eligibility = policy["eligibility"]
    results = objective.get("results") or {}
    _require(candidate_id in results, f"Candidato humano elegible ausente en evidencia objetiva: {candidate_id}.")
    record = results[candidate_id]
    candidate = record.get("candidate") or {}
    _require(candidate.get("id") == candidate_id, f"{candidate_id}: candidate.id inconsistente.")
    _require(candidate.get("treatment") is True, f"{candidate_id}: no es un tratamiento seleccionable.")

    required_cases = int(eligibility["required_noisy_cases"])
    noisy_cases = record.get("noisy_cases")
    _require(isinstance(noisy_cases, list) and len(noisy_cases) == required_cases, f"{candidate_id}: se requieren exactamente {required_cases} noisy cases.")
    noisy_ids = [str(item.get("id")) for item in noisy_cases]
    _require(len(set(noisy_ids)) == required_cases, f"{candidate_id}: noisy cases duplicados.")

    max_abs_delta = float(eligibility["maximum_absolute_raw_duration_delta_seconds"])
    si_deltas: list[float] = []
    stoi_deltas: list[float] = []
    positive_si_cases = 0
    positive_stoi_cases = 0
    max_observed_abs_delta = 0.0
    for item in noisy_cases:
        deltas = item.get("delta_vs_preserve") or {}
        si = float(deltas["si_sdr_db"])
        stoi = float(deltas["stoi"])
        _require(math.isfinite(si) and math.isfinite(stoi), f"{candidate_id}/{item.get('id')}: métricas no finitas.")
        si_deltas.append(si)
        stoi_deltas.append(stoi)
        positive_si_cases += int(si > 0.0)
        positive_stoi_cases += int(stoi > 0.0)
        timeline = item.get("timeline") or {}
        _validate_timeline(timeline=timeline, max_abs_delta=max_abs_delta, label=f"{candidate_id}/{item.get('id')}")
        max_observed_abs_delta = max(max_observed_abs_delta, abs(float(timeline.get("raw_duration_delta_seconds", 0.0))))

    mean_si = _mean(si_deltas, label=f"{candidate_id}.si_sdr_delta")
    mean_stoi = _mean(stoi_deltas, label=f"{candidate_id}.stoi_delta")
    summary_delta = (((record.get("noisy_summary") or {}).get("overall") or {}).get("delta_vs_preserve") or {})
    _require(_close(mean_si, float((summary_delta.get("si_sdr_db") or {})["mean"])), f"{candidate_id}: media SI-SDR no reproduce el summary congelado.")
    _require(_close(mean_stoi, float((summary_delta.get("stoi") or {})["mean"])), f"{candidate_id}: media STOI no reproduce el summary congelado.")

    clean_control = record.get("clean_control") or {}
    _require(clean_control.get("required") is True, f"{candidate_id}: falta clean control requerido.")
    clean_cases = clean_control.get("cases")
    _require(isinstance(clean_cases, list) and len(clean_cases) == required_cases, f"{candidate_id}: clean control debe contener {required_cases} casos.")
    clean_ids = [str(item.get("id")) for item in clean_cases]
    _require(len(set(clean_ids)) == required_cases, f"{candidate_id}: clean controls duplicados.")
    _require(set(clean_ids) == set(noisy_ids), f"{candidate_id}: clean controls no cubren exactamente los noisy cases.")
    for item in clean_cases:
        _validate_timeline(timeline=item.get("timeline") or {}, max_abs_delta=max_abs_delta, label=f"{candidate_id}/clean/{item.get('id')}")

    clean_summary = clean_control.get("summary") or {}
    _require(int(clean_summary.get("case_count", -1)) == required_cases, f"{candidate_id}: clean summary case_count inválido.")
    clean_stoi_mean = float((clean_summary.get("stoi") or {})["mean"])
    clean_nrmse_mean = float((clean_summary.get("normalized_rmse") or {})["mean"])
    _require(math.isfinite(clean_stoi_mean) and math.isfinite(clean_nrmse_mean), f"{candidate_id}: clean summary no finito.")

    objective_gate_pass = mean_si > 0.0 and mean_stoi > 0.0
    return {
        "candidate_id": candidate_id,
        "noisy_case_count": required_cases,
        "mean_delta_vs_preserve": {"si_sdr_db": mean_si, "stoi": mean_stoi},
        "positive_case_counts": {"si_sdr_db": positive_si_cases, "stoi": positive_stoi_cases},
        "maximum_observed_absolute_raw_duration_delta_seconds": max_observed_abs_delta,
        "clean_control_descriptive": {
            "case_count": required_cases,
            "stoi_mean": clean_stoi_mean,
            "normalized_rmse_mean": clean_nrmse_mean,
            "numeric_acceptance_threshold_applied": False,
        },
        "objective_aggregate_gate_pass": objective_gate_pass,
        "selection_eligible": objective_gate_pass,
    }


def build_denoiser_selection_review(*, objective_evidence: dict[str, Any], human_gate: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    _require(policy.get("schema_version") == 1 and policy.get("record_type") == "denoiser_selection_policy", "Selection policy schema inválido.")
    _require(policy.get("phase") == "3.6f", "Selection policy no corresponde a 3.6f.")
    _require(policy.get("frozen_after_evidence_before_selection") is True, "Selection policy no está marcada como congelada antes de seleccionar.")
    _validate_bindings(objective=objective_evidence, human_gate=human_gate, policy=policy)

    required_human_status = policy["eligibility"]["human_status_required"]
    human_eligible_ids: list[str] = []
    seen_treatments: set[str] = set()
    for pair in human_gate.get("pair_results") or []:
        treatment_id = str(pair.get("treatment_candidate_id"))
        _require(treatment_id not in seen_treatments, f"Human gate duplica tratamiento: {treatment_id}.")
        seen_treatments.add(treatment_id)
        if pair.get("perceptual_gate_pass") is True and pair.get("status") == required_human_status:
            human_eligible_ids.append(treatment_id)
        elif pair.get("perceptual_gate_pass") is True or pair.get("status") == required_human_status:
            raise ValueError(f"Human gate inconsistente para {treatment_id}.")

    evaluations = [
        _evaluate_candidate(candidate_id=candidate_id, objective=objective_evidence, policy=policy)
        for candidate_id in human_eligible_ids
    ]
    eligible = [item["candidate_id"] for item in evaluations if item["selection_eligible"]]

    if len(eligible) == 0:
        status = policy["decision_rule"]["zero_eligible_candidates"]
        selected: str | None = None
        selection_completed = True
    elif len(eligible) == 1:
        status = "SELECTED_FOR_INTEGRATION_REVIEW"
        selected = eligible[0]
        selection_completed = True
    else:
        status = policy["decision_rule"]["multiple_eligible_candidates"]
        selected = None
        selection_completed = False

    capabilities = policy["capabilities"]
    _require(capabilities.get("selection_can_change_product_default") is False, "Selection policy permitiría cambiar el default.")
    for key in ("denoise_authorized", "renderer_authorized", "auto_apply"):
        _require(capabilities.get(key) is False, f"Selection policy permitiría capability prohibida: {key}.")
    _require(capabilities.get("preserve_remains_product_default_until_separate_integration_and_execution_authorization") is True, "Selection policy no conserva preserve como default.")

    return {
        "schema_version": 1,
        "record_type": SELECTION_RECORD_TYPE,
        "policy_id": policy["policy_id"],
        "phase": "3.6f",
        "status": status,
        "selection_completed": selection_completed,
        "human_eligible_candidates": human_eligible_ids,
        "candidate_evaluations": evaluations,
        "selection_eligible_candidates": eligible,
        "selected_candidate_id": selected,
        "interpretation": {
            "selected_candidate_is_for_integration_review_only": selected is not None,
            "candidate_selection_review_complete": selection_completed,
            "product_default": "preserve",
            "product_default_changed": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }
