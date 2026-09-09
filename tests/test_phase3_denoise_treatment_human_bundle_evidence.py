import hashlib
import json
import unittest
from pathlib import Path

from video_tunner.denoise_treatment_human_closeout import validate_integrated_bundle_technical_evidence


ROOT = Path(__file__).resolve().parents[1]
PRECOMMIT = ROOT / "Validation" / "phase3-denoise-treatment-human-closeout-precommit.json"
TECHNICAL = ROOT / "Validation" / "phase3-denoise-treatment-human-bundle-technical.json"
PROVENANCE = ROOT / "Validation" / "phase3-denoise-treatment-human-bundle-provenance.json"
WORKFLOW = ROOT / ".github" / "workflows" / "phase3-denoise-treatment-human-closeout.yml"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase3DenoiseTreatmentHumanBundleEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
        cls.technical = json.loads(TECHNICAL.read_text(encoding="utf-8"))
        cls.provenance = json.loads(PROVENANCE.read_text(encoding="utf-8"))
        cls.precommit_sha = sha256_path(PRECOMMIT)

    def test_persisted_technical_evidence_validates_against_exact_precommit(self):
        result = validate_integrated_bundle_technical_evidence(
            technical_evidence=self.technical,
            precommit=self.precommit,
            expected_precommit_sha256=self.precommit_sha,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["case_count"], 10)
        self.assertEqual(result["technical_pass_count"], 10)
        self.assertEqual(result["public_bundle_manifest_sha256"], "39499e5349e1ad22def6b8b3c60359f2de2548e924421a363a8d38ebcc8b1b08")

    def test_persisted_serialization_sha_is_frozen_and_documented(self):
        self.assertEqual(sha256_path(TECHNICAL), "37d11ec3ae4115ba63d38fac5ff27a156c2e46dde7274be5a7c8084f143ec0f0")
        self.assertEqual(
            self.provenance["technical_evidence"]["persisted_semantic_equivalent_minified_sha256"],
            sha256_path(TECHNICAL),
        )
        self.assertEqual(
            self.provenance["technical_evidence"]["artifact_raw_json_sha256"],
            "54edf6f01ad06828e01b9ae216cfb3f4330f66b4a62f14910ccd3703a84b5c6b",
        )

    def test_run_and_artifact_provenance_are_exact(self):
        workflow = self.provenance["workflow"]
        self.assertEqual(workflow["run_id"], 34342953064)
        self.assertEqual(workflow["job_id"], 102437776572)
        self.assertEqual(workflow["head_sha"], "809112e755ded9f4c17388228058c012b473b6b6")
        self.assertEqual(workflow["preflight"], "17/17 PASS")
        self.assertEqual(workflow["integrated_technical_cases"], "10/10 PASS")
        self.assertEqual(workflow["technical_fail_count"], 0)
        self.assertEqual(workflow["invalid_or_stale_count"], 0)
        self.assertEqual(workflow["independent_bundle_validation"], "PASS")

        public = self.provenance["public_bundle"]
        self.assertEqual(public["artifact_id"], 10100571018)
        self.assertEqual(public["artifact_zip_sha256"], "b11143f72fc8bc3219dcaf7d4ed82afa6d628febf80b4b6efc444977f8d51c90")
        self.assertEqual(public["wav_hashes_verified"], "30/30")
        self.assertEqual(public["ab_frame_match"], "10/10")
        self.assertEqual(public["blinding_leaks"], 0)

        private = self.provenance["technical_evidence"]
        self.assertEqual(private["artifact_id"], 10100571445)
        self.assertEqual(private["artifact_zip_sha256"], "ac958b8c02c1f8ce7cd7998d2f3f1a0146db259fa59ca0f49186db5147639504")

    def test_human_state_is_still_pending_and_unattributed(self):
        self.assertEqual(self.provenance["public_bundle"]["human_review_status"], "PENDING_HUMAN_REVIEW")
        state = self.provenance["actual_human_state"]
        self.assertFalse(state["human_listening_completed"])
        self.assertFalse(state["human_review_persisted"])
        self.assertFalse(state["human_closeout_evaluated"])

    def test_capabilities_remain_preserve_and_non_executable_for_user_media(self):
        caps = self.provenance["capabilities"]
        self.assertFalse(caps["real_guille_authorization_created"])
        self.assertFalse(caps["real_guille_media_processed"])
        self.assertEqual(caps["product_default"], "preserve")
        self.assertFalse(caps["auto_apply"])
        self.assertFalse(caps["stereo_or_multichannel_generalized"])

    def test_permanent_workflow_is_manual_only(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("\n  push:", text)
        self.assertIn("phase3-denoise-treatment-human-closeout-review-bundle", text)
        self.assertIn("phase3-denoise-treatment-human-closeout-technical-evidence", text)

    def test_no_temporary_trigger_remains_in_head(self):
        self.assertFalse((ROOT / ".github" / "phase3-denoise-treatment-human-closeout.trigger").exists())


if __name__ == "__main__":
    unittest.main()
