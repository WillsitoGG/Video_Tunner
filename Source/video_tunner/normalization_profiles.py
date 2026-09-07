from __future__ import annotations

from typing import Any

DEFAULT_NORMALIZATION_PROFILE = "preserve"
EBU_R128_PROGRAMME_PROFILE = "ebu_r128_programme"

NORMALIZATION_PROFILES: dict[str, dict[str, Any]] = {
    DEFAULT_NORMALIZATION_PROFILE: {
        "name": DEFAULT_NORMALIZATION_PROFILE,
        "description": "Preserve the validated render audio without loudness normalization.",
        "target_lufs": None,
        "max_true_peak_dbtp": None,
        "standard": None,
        "standard_version": None,
        "measurement_basis": None,
        "treatment_requested": False,
    },
    EBU_R128_PROGRAMME_PROFILE: {
        "name": EBU_R128_PROGRAMME_PROFILE,
        "description": "EBU R 128 programme-loudness target for explicit standards-based normalization review.",
        "target_lufs": -23.0,
        "max_true_peak_dbtp": -1.0,
        "standard": "EBU R 128",
        "standard_version": "5.0 (November 2023)",
        "measurement_basis": "ITU-R BS.1770-5 (November 2023)",
        "treatment_requested": True,
    },
}


def normalization_profile(name: str) -> dict[str, Any]:
    profile_name = str(name or "").strip()
    if profile_name not in NORMALIZATION_PROFILES:
        raise ValueError(f"Normalization profile no soportado: {profile_name}")
    return dict(NORMALIZATION_PROFILES[profile_name])


def build_normalization_profile_decision(
    treatment_decision: dict[str, Any],
    *,
    profile_name: str = DEFAULT_NORMALIZATION_PROFILE,
) -> dict[str, Any]:
    """Select a standards profile without authorizing media processing.

    `preserve` is the product default. A standards-based profile is an explicit
    opt-in review request only; this layer never builds an FFmpeg filter, renders
    media or infers that a measured risk means a particular target should be used.
    """
    if not isinstance(treatment_decision, dict):
        raise ValueError("Treatment decision debe ser un objeto JSON.")
    if treatment_decision.get("schema_version") != 1:
        raise ValueError("Treatment decision schema no soportado.")
    if treatment_decision.get("record_type") != "audiovisual_treatment_decision":
        raise ValueError("Treatment decision record_type inválido.")
    if treatment_decision.get("executable") or treatment_decision.get("treatment_authorized") or treatment_decision.get("auto_apply"):
        raise ValueError("Treatment decision upstream no puede contener capacidad ejecutable.")

    binding = treatment_decision.get("quality_audit_binding")
    if not isinstance(binding, dict) or not str(binding.get("output_sha256") or ""):
        raise ValueError("Treatment decision sin output binding.")

    profile = normalization_profile(profile_name)
    preserve = profile_name == DEFAULT_NORMALIZATION_PROFILE
    return {
        "schema_version": 1,
        "record_type": "normalization_profile_decision",
        "status": "preserve_selected" if preserve else "normalization_profile_review_selected",
        "quality_output_sha256": binding["output_sha256"],
        "profile": profile,
        "explicit_opt_in_required": not preserve,
        "human_approval_required": not preserve,
        "normalization_requested": not preserve,
        "normalization_authorized": False,
        "parameters_executable": False,
        "render_authorized": False,
        "auto_apply": False,
    }
