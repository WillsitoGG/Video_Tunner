from __future__ import annotations

import json
import unittest
from pathlib import Path

from video_tunner.denoise_runtime import selected_denoiser_contract


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "Validation" / "phase3-denoiser-portable-runtime.json"
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_candidate_comparison_policy_v1.json"
SELECTION = ROOT / "Validation" / "phase3-denoiser-selection-review.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Phase3DenoiserPortableRuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.evidence = load(EVIDENCE)
        self.policy = load(POLICY)
        self.selection = load(SELECTION)
        self.contract = selected_denoiser_contract()

    def test_closeout_identity_is_exactly_bound_to_selected_candidate_and_frozen_policy(self):
        evidence = self.evidence["selected_denoiser"]
        frozen = next(
            candidate
            for candidate in self.policy["candidates"]
            if candidate["id"] == self.selection["selected_candidate_id"]
        )

        self.assertEqual(self.evidence["phase"], "3.6g")
        self.assertEqual(self.evidence["status"], "CLOSED")
        self.assertEqual(evidence["candidate_id"], self.selection["selected_candidate_id"])
        self.assertEqual(evidence["candidate_id"], self.contract["candidate_id"])
        self.assertEqual(evidence["version"], frozen["version"])
        self.assertEqual(evidence["upstream_asset_url"], frozen["asset_url"])
        self.assertEqual(evidence["asset_sha256"], frozen["asset_sha256"])
        self.assertEqual(evidence["asset_size_bytes"], frozen["asset_size_bytes"])
        self.assertEqual(evidence["arguments"], frozen["arguments"])
        self.assertEqual(evidence["explicit_model_argument"], frozen["explicit_model_argument"])

    def test_portable_contract_is_exactly_the_runtime_contract_and_forbids_runtime_acquisition(self):
        evidence = self.evidence["selected_denoiser"]
        portable = self.evidence["portable_contract"]

        self.assertEqual(evidence["runtime_relative_path"], self.contract["runtime_relative_path"])
        self.assertEqual(portable["asset_acquisition_stage"], "build_only")
        self.assertFalse(portable["runtime_download_allowed"])
        self.assertFalse(portable["path_lookup_allowed"])
        self.assertEqual(portable["media_contract"], self.contract["media_contract"])
        self.assertIn("sha256", portable["identity_verification"]["before_bundle_copy"])
        self.assertIn("sha256", portable["identity_verification"]["after_bundle_copy"])

    def test_successful_validation_provenance_is_exact_and_all_required_gates_passed(self):
        validation = self.evidence["validation"]

        self.assertEqual(validation["successful_workflow_run_id"], 34211660270)
        self.assertEqual(validation["successful_job_id"], 102013916505)
        self.assertEqual(validation["validated_head_sha"], "1db1bdd516292b00136e45a3c92b53b18f59b29f")
        self.assertEqual(validation["focused_contract_tests"], {"ran": 14, "result": "PASS"})
        self.assertEqual(validation["portable_build"], "PASS")
        self.assertEqual(validation["portable_provenance_gate"], "PASS")
        self.assertEqual(validation["offline_smoke"]["result"], "PASS")
        self.assertEqual(validation["tamper_fail_closed"]["result"], "PASS")
        self.assertEqual(validation["integrated_regression"]["ran"], 418)
        self.assertEqual(validation["integrated_regression"]["result"], "PASS")
        self.assertEqual(validation["development_doctor"], "PASS")
        self.assertEqual(validation["portable_doctor"], "PASS")

    def test_offline_smoke_stays_inside_precommitted_media_timeline_contract(self):
        smoke = self.evidence["validation"]["offline_smoke"]
        media = self.contract["media_contract"]

        self.assertEqual(smoke["outbound_network_for_exact_executable"], "BLOCKED")
        self.assertFalse(smoke["runtime_download_performed"])
        self.assertEqual(smoke["output_channels"], media["output_channels"])
        self.assertEqual(smoke["output_sample_rate_hz"], media["output_sample_rate_hz"])
        self.assertLessEqual(
            abs(smoke["raw_duration_delta_seconds"]),
            media["raw_duration_delta_max_seconds"],
        )

    def test_tamper_gate_and_artifact_provenance_are_frozen(self):
        validation = self.evidence["validation"]
        tamper = validation["tamper_fail_closed"]
        artifact = validation["artifact"]

        self.assertEqual(tamper["mutation"], "append_one_byte")
        self.assertEqual(tamper["observed_tampered_size_bytes"], tamper["expected_size_bytes"] + 1)
        self.assertEqual(tamper["rejection_class"], "size_mismatch")
        self.assertEqual(artifact["id"], 10050110122)
        self.assertEqual(
            artifact["zip_sha256"],
            "c27f8a0ddfaa88bfdfa36bf8c79d6b4ec74198669f75cbfbb427648c6d04de89",
        )

    def test_closeout_cannot_smuggle_denoise_execution_capability(self):
        state = self.evidence["product_state_after_closeout"]
        contract_state = self.contract["integration_state"]

        self.assertTrue(state["selected_for_integration_review_only"])
        self.assertEqual(state["product_default"], "preserve")
        self.assertFalse(state["denoise_authorized"])
        self.assertFalse(state["renderer_authorized"])
        self.assertFalse(state["auto_apply"])
        self.assertFalse(state["denoise_renderer_present"])
        self.assertFalse(contract_state["denoise_authorized"])
        self.assertFalse(contract_state["renderer_authorized"])
        self.assertFalse(contract_state["auto_apply"])


if __name__ == "__main__":
    unittest.main()
