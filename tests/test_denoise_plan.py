import copy
import unittest
from unittest.mock import patch

from video_tunner.denoise_plan import build_denoise_plan_proposal, validate_denoise_plan_proposal
from video_tunner.denoise_runtime import SELECTED_DENOISER_ID, selected_denoiser_contract


NOISE_SHA = "a" * 64
SELECTION_SHA = "b" * 64
QUALITY_SHA = "c" * 64
OUTPUT_SHA = "d" * 64


def noise_audit(*, sufficient=True):
    return {
        "schema_version": 1,
        "record_type": "noise_evidence_audit",
        "status": "noise_measurement_complete" if sufficient else "insufficient_noise_evidence",
        "valid": True,
        "evidence_sufficient": sufficient,
        "quality_binding": {
            "quality_audit_sha256": QUALITY_SHA,
            "required_quality_status": "quality_audit_complete",
            "output_sha256": OUTPUT_SHA,
        },
        "window_evidence": {"speech_evidence_sha256": "e" * 64},
        "coverage": {"non_speech_window_count": 2 if sufficient else 1, "non_speech_seconds": 2.5 if sufficient else 0.5},
        "measurements": {"non_speech_energy": {"median_rms_dbfs": -42.0}},
        "interpretation": {"threshold_note": "No measured dBFS value is a denoise threshold."},
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


def selection_review():
    return {
        "schema_version": 1,
        "record_type": "denoiser_selection_review",
        "policy_id": "phase3_denoiser_selection_review_v1",
        "phase": "3.6f",
        "status": "SELECTED_FOR_INTEGRATION_REVIEW",
        "selection_completed": True,
        "human_eligible_candidates": [SELECTED_DENOISER_ID],
        "candidate_evaluations": [
            {
                "candidate_id": SELECTED_DENOISER_ID,
                "objective_aggregate_gate_pass": True,
                "selection_eligible": True,
            }
        ],
        "selection_eligible_candidates": [SELECTED_DENOISER_ID],
        "selected_candidate_id": SELECTED_DENOISER_ID,
        "interpretation": {
            "selected_candidate_is_for_integration_review_only": True,
            "candidate_selection_review_complete": True,
            "product_default": "preserve",
            "product_default_changed": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }


def build(*, sufficient=True):
    audit = noise_audit(sufficient=sufficient)
    selection = selection_review()
    plan = build_denoise_plan_proposal(
        audit,
        selection,
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        current_output_sha256=OUTPUT_SHA,
    )
    return audit, selection, plan


def validate(audit, selection, plan, *, output_sha=OUTPUT_SHA):
    return validate_denoise_plan_proposal(
        audit,
        selection,
        plan,
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        current_output_sha256=output_sha,
    )


class DenoisePlanProposalTests(unittest.TestCase):
    def test_ready_plan_freezes_selected_runtime_without_execution_capability(self):
        audit, selection, plan = build()
        self.assertEqual(plan["status"], "denoise_plan_proposal_ready")
        self.assertTrue(plan["ready_for_execution_authorization"])
        self.assertEqual(plan["bindings"]["quality_output_sha256"], OUTPUT_SHA)
        self.assertEqual(plan["bindings"]["selected_candidate_id"], SELECTED_DENOISER_ID)
        self.assertEqual(plan["runtime"]["arguments_template"], ["--compensate-delay", "--output-dir", "<output_dir>", "<input_wav>"])
        self.assertEqual(plan["media_contract"]["raw_duration_delta_max_seconds"], 0.05)
        self.assertEqual(plan["policy"]["noise_evidence_role"], "measurement_coverage_only_not_treatment_trigger")
        self.assertEqual(plan["policy"]["product_default"], "preserve")
        self.assertTrue(plan["parameters_defined"])
        for key in ("parameters_executable", "denoise_authorized", "denoise_render_authorization", "plan_render_authorization", "renderer_available", "executable", "auto_apply"):
            self.assertFalse(plan[key])
        self.assertEqual(validate(audit, selection, plan)["status"], "valid_ready")

    def test_insufficient_measurement_coverage_blocks_without_claiming_denoise_need(self):
        audit, selection, plan = build(sufficient=False)
        self.assertEqual(plan["status"], "denoise_plan_blocked")
        self.assertFalse(plan["ready_for_execution_authorization"])
        self.assertEqual(plan["blockers"][0]["code"], "insufficient_noise_measurement_coverage")
        self.assertIn("not evidence that denoise is needed", plan["blockers"][0]["meaning"])
        result = validate(audit, selection, plan)
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], "valid_blocked")

    def test_current_output_sha_mismatch_fails_closed(self):
        audit, selection, plan = build()
        result = validate(audit, selection, plan, output_sha="9" * 64)
        self.assertEqual(result["status"], "stale_or_invalid_upstream")
        self.assertFalse(result["valid"])

    def test_noise_audit_tamper_invalidates_plan_even_when_file_sha_argument_is_unchanged(self):
        audit, selection, plan = build()
        changed = copy.deepcopy(audit)
        changed["measurements"]["non_speech_energy"]["median_rms_dbfs"] = -20.0
        result = validate(changed, selection, plan)
        self.assertEqual(result["status"], "stale_or_tampered_plan")
        self.assertFalse(result["valid"])

    def test_selection_review_tamper_invalidates_plan(self):
        audit, selection, plan = build()
        changed = copy.deepcopy(selection)
        changed["candidate_evaluations"][0]["selection_eligible"] = False
        result = validate(audit, changed, plan)
        self.assertEqual(result["status"], "stale_or_invalid_upstream")
        self.assertFalse(result["valid"])

    def test_runtime_contract_drift_invalidates_existing_plan(self):
        audit, selection, plan = build()
        changed_contract = selected_denoiser_contract()
        changed_contract["asset_sha256"] = "f" * 64
        with patch("video_tunner.denoise_plan.selected_denoiser_contract", return_value=changed_contract):
            result = validate(audit, selection, plan)
        self.assertEqual(result["status"], "stale_or_tampered_plan")
        self.assertFalse(result["valid"])

    def test_upstream_capability_tamper_fails_closed(self):
        audit = noise_audit()
        audit["treatment_policy"]["denoise_authorized"] = True
        with self.assertRaises(ValueError):
            build_denoise_plan_proposal(
                audit,
                selection_review(),
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                current_output_sha256=OUTPUT_SHA,
            )

    def test_plan_capability_tamper_is_rejected(self):
        audit, selection, plan = build()
        for field in ("parameters_executable", "denoise_authorized", "denoise_render_authorization", "plan_render_authorization", "renderer_available", "executable", "auto_apply"):
            tampered = copy.deepcopy(plan)
            tampered[field] = True
            result = validate(audit, selection, tampered)
            self.assertEqual(result["status"], "invalid_record")
            self.assertFalse(result["valid"])

    def test_invalid_provenance_sha_is_rejected(self):
        with self.assertRaises(ValueError):
            build_denoise_plan_proposal(
                noise_audit(),
                selection_review(),
                noise_audit_sha256="bad",
                selection_review_sha256=SELECTION_SHA,
                current_output_sha256=OUTPUT_SHA,
            )


if __name__ == "__main__":
    unittest.main()
