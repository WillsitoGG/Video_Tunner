import copy
import unittest

from video_tunner.denoise_execution_authorization import (
    build_denoise_execution_authorization,
    validate_denoise_execution_authorization,
)
from video_tunner.denoise_plan import build_denoise_plan_proposal
from video_tunner.denoise_runtime import SELECTED_DENOISER_ID


NOISE_SHA = "a" * 64
SELECTION_SHA = "b" * 64
PLAN_SHA = "c" * 64
QUALITY_SHA = "d" * 64
OUTPUT_SHA = "e" * 64


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
        "window_evidence": {"speech_evidence_sha256": "f" * 64},
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


def chain(*, sufficient=True):
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


def authorize(audit, selection, plan, *, decision="APPROVE", actor="Test Reviewer", reason="Authorize only the future gated denoise renderer path."):
    return build_denoise_execution_authorization(
        audit,
        selection,
        plan,
        decision=decision,
        actor=actor,
        reason=reason,
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        plan_sha256=PLAN_SHA,
        current_output_sha256=OUTPUT_SHA,
        created_utc="2026-09-08T11:30:00+00:00",
    )


def validate(audit, selection, plan, authorization, *, plan_sha=PLAN_SHA, output_sha=OUTPUT_SHA):
    return validate_denoise_execution_authorization(
        audit,
        selection,
        plan,
        authorization,
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        plan_sha256=plan_sha,
        current_output_sha256=output_sha,
    )


class DenoiseExecutionAuthorizationTests(unittest.TestCase):
    def test_approve_authorizes_only_future_gated_renderer_not_current_execution(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        result = validate(audit, selection, plan, authorization)
        self.assertEqual(result["status"], "valid_authorized")
        self.assertTrue(result["authorized"])
        self.assertTrue(result["denoise_render_authorization"])
        self.assertFalse(result["plan_render_authorization"])
        self.assertFalse(result["parameters_executable"])
        self.assertFalse(result["renderer_available"])
        self.assertFalse(result["executable"])
        self.assertFalse(result["auto_apply"])
        self.assertEqual(authorization["authorization_state"], "authorized_for_future_gated_renderer")

    def test_reject_is_valid_and_grants_no_render_authorization(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan, decision="REJECT")
        result = validate(audit, selection, plan, authorization)
        self.assertEqual(result["status"], "valid_rejected")
        self.assertTrue(result["valid"])
        self.assertFalse(result["authorized"])
        self.assertFalse(result["denoise_render_authorization"])

    def test_actor_and_reason_are_required(self):
        audit, selection, plan = chain()
        with self.assertRaises(ValueError):
            authorize(audit, selection, plan, actor="")
        with self.assertRaises(ValueError):
            authorize(audit, selection, plan, reason="")

    def test_blocked_plan_cannot_receive_authorization(self):
        audit, selection, plan = chain(sufficient=False)
        self.assertEqual(plan["status"], "denoise_plan_blocked")
        with self.assertRaises(ValueError):
            authorize(audit, selection, plan)

    def test_changed_plan_sha_marks_authorization_stale(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        result = validate(audit, selection, plan, authorization, plan_sha="1" * 64)
        self.assertEqual(result["status"], "stale_plan")
        self.assertFalse(result["authorized"])

    def test_changed_output_sha_invalidates_authorization_chain(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        result = validate(audit, selection, plan, authorization, output_sha="2" * 64)
        self.assertEqual(result["status"], "stale_or_invalid_plan")
        self.assertFalse(result["authorized"])

    def test_tampered_noise_evidence_invalidates_authorization(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        changed = copy.deepcopy(audit)
        changed["measurements"]["non_speech_energy"]["median_rms_dbfs"] = -10.0
        result = validate(changed, selection, plan, authorization)
        self.assertEqual(result["status"], "stale_or_invalid_plan")
        self.assertFalse(result["authorized"])

    def test_tampered_selection_invalidates_authorization(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        changed = copy.deepcopy(selection)
        changed["selected_candidate_id"] = "other_candidate"
        result = validate(audit, changed, plan, authorization)
        self.assertEqual(result["status"], "stale_or_invalid_plan")
        self.assertFalse(result["authorized"])

    def test_tampered_plan_is_rebuilt_and_rejected(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        tampered = copy.deepcopy(plan)
        tampered["runtime"]["arguments_template"] = ["--output-dir", "<output_dir>", "<input_wav>"]
        result = validate(audit, selection, tampered, authorization)
        self.assertEqual(result["status"], "stale_or_invalid_plan")
        self.assertFalse(result["authorized"])

    def test_authorization_capability_tampering_is_rejected(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        for field in ("plan_render_authorization", "parameters_executable", "renderer_available", "executable", "auto_apply"):
            tampered = copy.deepcopy(authorization)
            tampered[field] = True
            result = validate(audit, selection, plan, tampered)
            self.assertEqual(result["status"], "invalid_record")
            self.assertFalse(result["authorized"])

    def test_render_authorization_must_match_explicit_decision(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan, decision="REJECT")
        authorization["denoise_render_authorization"] = True
        result = validate(audit, selection, plan, authorization)
        self.assertEqual(result["status"], "invalid_record")
        self.assertFalse(result["authorized"])

    def test_snapshot_binds_selected_candidate_and_runtime_fingerprint(self):
        audit, selection, plan = chain()
        authorization = authorize(audit, selection, plan)
        self.assertEqual(authorization["selected_candidate_id"], SELECTED_DENOISER_ID)
        self.assertEqual(
            authorization["runtime_contract_fingerprint"],
            plan["bindings"]["runtime_contract_fingerprint"],
        )
        self.assertEqual(authorization["quality_output_sha256"], OUTPUT_SHA)


if __name__ == "__main__":
    unittest.main()
