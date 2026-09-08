import json
import unittest
from pathlib import Path

from video_tunner.denoise_execution_authorization import (
    DENOISE_EXECUTION_AUTHORIZATION_RECORD_TYPE,
    DENOISE_EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
)
from video_tunner.denoise_plan import (
    DENOISE_PLAN_POLICY_ID,
    DENOISE_PLAN_RECORD_TYPE,
    DENOISE_PLAN_SCHEMA_VERSION,
)
from video_tunner.denoise_runtime import (
    DEEPFILTER_ARGUMENTS,
    DEEPFILTER_ASSET_SHA256,
    DEEPFILTER_ASSET_SIZE_BYTES,
    DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
    DEEPFILTER_RUNTIME_RELATIVE_PATH,
    DEEPFILTER_VERSION,
    SELECTED_DENOISER_ID,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "Validation" / "phase3-denoise-plan-authorization-foundation.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "phase3-denoise-plan-authorization.yml"


class Phase3DenoisePlanAuthorizationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_foundation_identity_and_successful_validation_are_frozen(self):
        evidence = self.evidence
        self.assertEqual(evidence["schema_version"], 1)
        self.assertEqual(evidence["record_type"], "phase3_denoise_plan_authorization_foundation")
        self.assertEqual(evidence["phase"], "3.6h")
        self.assertEqual(evidence["status"], "TECHNICAL_FOUNDATION_PASS")
        validation = evidence["validation"]
        self.assertEqual(validation["run_id"], 34220351609)
        self.assertEqual(validation["job_id"], 102041750032)
        self.assertEqual(validation["head_sha"], "ec5409066003472614c7f838789de789123d58be")
        self.assertEqual(validation["focused_tests"], "38/38 PASS")
        self.assertEqual(validation["integrated_tests"], "445/445 PASS")
        self.assertEqual(validation["doctor"], "PASS")
        self.assertTrue(validation["scope_note_pass"])

    def test_persisted_schema_and_policy_match_implementation_constants(self):
        implementation = self.evidence["implementation"]
        self.assertEqual(implementation["plan_schema_version"], DENOISE_PLAN_SCHEMA_VERSION)
        self.assertEqual(implementation["plan_record_type"], DENOISE_PLAN_RECORD_TYPE)
        self.assertEqual(implementation["plan_policy_id"], DENOISE_PLAN_POLICY_ID)
        self.assertEqual(
            implementation["authorization_schema_version"],
            DENOISE_EXECUTION_AUTHORIZATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            implementation["authorization_record_type"],
            DENOISE_EXECUTION_AUTHORIZATION_RECORD_TYPE,
        )
        self.assertEqual(implementation["decisions"], ["APPROVE", "REJECT"])

    def test_persisted_runtime_binding_matches_exact_selected_3_6g_contract(self):
        bindings = self.evidence["bindings"]
        self.assertEqual(bindings["selected_candidate_id"], SELECTED_DENOISER_ID)
        self.assertEqual(bindings["deepfilter_version"], DEEPFILTER_VERSION)
        self.assertEqual(bindings["deepfilter_asset_sha256"], DEEPFILTER_ASSET_SHA256)
        self.assertEqual(bindings["deepfilter_asset_size_bytes"], DEEPFILTER_ASSET_SIZE_BYTES)
        self.assertEqual(bindings["runtime_relative_path"], DEEPFILTER_RUNTIME_RELATIVE_PATH.as_posix())
        self.assertEqual(bindings["arguments_template"], DEEPFILTER_ARGUMENTS)
        self.assertEqual(
            bindings["raw_duration_delta_max_seconds"],
            DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
        )
        self.assertEqual(bindings["noise_evidence_role"], "measurement_coverage_only_not_treatment_trigger")

    def test_foundation_cannot_be_misread_as_real_user_authorization_or_renderer(self):
        state = self.evidence["actual_product_state"]
        self.assertFalse(state["real_user_authorization_record_created"])
        self.assertFalse(state["real_user_media_authorized_for_denoise"])
        self.assertFalse(state["denoise_renderer_implemented"])
        self.assertFalse(state["treated_media_generated"])
        self.assertEqual(state["product_default"], "preserve")
        self.assertFalse(state["product_default_changed"])
        self.assertFalse(state["auto_apply"])
        interpretation = self.evidence["interpretation"]
        self.assertTrue(interpretation["contract_approve_path_tested_with_synthetic_fixture_only"])
        self.assertTrue(interpretation["guille_did_not_issue_a_real_per_media_denoise_authorization_in_3_6h"])

    def test_plan_and_authorization_capability_boundaries_remain_non_executable(self):
        plan = self.evidence["plan_contract"]
        self.assertTrue(plan["insufficient_noise_measurement_coverage_blocks_plan"])
        self.assertTrue(plan["insufficient_coverage_is_not_interpreted_as_denoise_need"])
        self.assertTrue(plan["noise_evidence_fingerprint_bound"])
        self.assertTrue(plan["selection_review_fingerprint_bound"])
        self.assertTrue(plan["runtime_contract_fingerprint_bound"])
        for key in (
            "parameters_executable",
            "denoise_authorized",
            "denoise_render_authorization",
            "plan_render_authorization",
            "renderer_available",
            "executable",
            "auto_apply",
        ):
            self.assertFalse(plan[key])

        authorization = self.evidence["authorization_contract"]
        self.assertTrue(authorization["explicit_actor_required"])
        self.assertTrue(authorization["explicit_reason_required"])
        self.assertTrue(authorization["approve_can_grant_only_future_gated_denoise_render_authorization"])
        self.assertTrue(authorization["approve_does_not_make_parameters_executable"])
        self.assertTrue(authorization["approve_does_not_make_renderer_available"])
        self.assertTrue(authorization["approve_does_not_make_record_executable"])
        self.assertFalse(authorization["plan_render_authorization"])
        self.assertFalse(authorization["auto_apply"])

    def test_all_stale_and_tamper_guards_are_persisted_as_required(self):
        authorization = self.evidence["authorization_contract"]
        for key in (
            "stale_plan_sha_fails_closed",
            "stale_output_sha_fails_closed",
            "tampered_noise_evidence_fails_closed",
            "tampered_selection_fails_closed",
            "tampered_plan_fails_closed",
            "capability_tampering_fails_closed",
        ):
            self.assertTrue(authorization[key])

    def test_permanent_gate_is_manual_only_and_includes_persisted_evidence_binder(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("tests.test_phase3_denoise_plan_authorization_evidence", workflow)
        self.assertIn("No real user media is authorized", workflow)
        self.assertIn("no denoise renderer exists", workflow)


if __name__ == "__main__":
    unittest.main()
