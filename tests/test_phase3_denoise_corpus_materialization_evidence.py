import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
EVIDENCE = ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
EXPECTED_FIXTURE_SHA256 = "49e742ce7912d008ee5ef3cc3bd5a31b4c9f117125aa2a811b2a6bd00acb1c03"
EXPECTED_RAW_MANIFEST_SHA256 = "f6e73738a4be3b07b3126472e90b8bbc891246781b15a85e3c98367b08c068c1"
EXPECTED_ARTIFACT_ZIP_SHA256 = "d5c3ee7890ee0c5a1efb5241a7edba3b3145bfa9f917ecc77d3f4a5310c96ddd"


class Phase3DenoiseCorpusMaterializationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    def test_materialization_is_bound_to_exact_frozen_fixture(self):
        actual_fixture_sha = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(actual_fixture_sha, EXPECTED_FIXTURE_SHA256)
        self.assertEqual(self.evidence["fixture_sha256"], actual_fixture_sha)
        self.assertEqual(self.evidence["corpus_id"], self.fixture["corpus_id"])
        self.assertEqual(self.evidence["case_count"], 40)

    def test_archive_identity_matches_publisher_checksums_frozen_in_fixture(self):
        for key in ("clean_testset", "noisy_testset", "logfiles"):
            self.assertEqual(
                self.evidence["archive_md5"][key],
                self.fixture["archives"][key]["md5"],
            )
            self.assertEqual(self.evidence["transport"][key], "edinburgh_legacy")

    def test_all_materialized_pairs_match_precommitted_cells_and_have_valid_hashes(self):
        fixture_cases = {
            case["id"]: (case["speaker"], case["noise"], float(case["snr_db"]))
            for case in self.fixture["cases"]
        }
        evidence_cases = self.evidence["cases"]
        self.assertEqual({case["id"] for case in evidence_cases}, set(fixture_cases))
        for case in evidence_cases:
            self.assertEqual(
                (case["speaker"], case["noise"], float(case["snr_db"])),
                fixture_cases[case["id"]],
            )
            for field in ("clean_sha256", "noisy_sha256"):
                value = case[field]
                self.assertEqual(len(value), 64)
                int(value, 16)
            self.assertNotEqual(case["clean_sha256"], case["noisy_sha256"])
            self.assertEqual(case["sample_rate_hz"], 48000)
            self.assertGreater(case["frame_count"], 0)
            self.assertGreater(case["duration_seconds"], 0.0)

    def test_materialization_remains_evaluation_only_and_provenance_is_frozen(self):
        policy = self.evidence["evaluation_policy"]
        self.assertTrue(policy["clean_reference_required"])
        self.assertTrue(policy["objective_metrics_are_auxiliary_only"])
        self.assertTrue(policy["human_perceptual_comparison_required_before_treatment_authorization"])
        self.assertFalse(policy["denoiser_selected"])
        self.assertFalse(policy["denoise_authorized"])
        self.assertFalse(policy["renderer_authorized"])
        self.assertFalse(policy["auto_apply"])

        provenance = self.evidence["provenance"]
        self.assertEqual(provenance["workflow_run_id"], 34142222451)
        self.assertEqual(provenance["workflow_artifact_id"], 10026385254)
        self.assertEqual(provenance["raw_manifest_sha256"], EXPECTED_RAW_MANIFEST_SHA256)
        self.assertEqual(provenance["artifact_zip_sha256"], EXPECTED_ARTIFACT_ZIP_SHA256)


if __name__ == "__main__":
    unittest.main()
