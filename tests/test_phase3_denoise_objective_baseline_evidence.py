import hashlib
import json
import math
import statistics
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoise_objective_metric_policy_v1.json"
MATERIALIZATION = ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
BASELINE = ROOT / "Validation" / "phase3-denoise-objective-baseline.json"

EXPECTED_CORPUS_SHA256 = "49e742ce7912d008ee5ef3cc3bd5a31b4c9f117125aa2a811b2a6bd00acb1c03"
EXPECTED_POLICY_SHA256 = "914e015140c933d201ca9e61d8d54c2a97579a44d748e8a5c3fb99c38da791b1"
EXPECTED_MATERIALIZATION_SHA256 = "aade84868bbdc469e3b862d5a6509f96c5570354ea43e8c5d12fa5da434d1ff1"
EXPECTED_RAW_BASELINE_SHA256 = "0c11cf701618d461cd1144a817edc77f75225333b306f91310a972475cb183fe"
EXPECTED_ARTIFACT_ZIP_SHA256 = "f3bab585a479f30787cb75ffb0a664a647f61168af2409e84645da2d2a92cad3"


class Phase3DenoiseObjectiveBaselineEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.materialization = json.loads(MATERIALIZATION.read_text(encoding="utf-8"))
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_baseline_is_bound_to_exact_frozen_inputs(self):
        self.assertEqual(hashlib.sha256(CORPUS.read_bytes()).hexdigest(), EXPECTED_CORPUS_SHA256)
        self.assertEqual(hashlib.sha256(POLICY.read_bytes()).hexdigest(), EXPECTED_POLICY_SHA256)
        self.assertEqual(hashlib.sha256(MATERIALIZATION.read_bytes()).hexdigest(), EXPECTED_MATERIALIZATION_SHA256)
        bindings = self.baseline["bindings"]
        self.assertEqual(bindings["corpus_fixture_sha256"], EXPECTED_CORPUS_SHA256)
        self.assertEqual(bindings["metric_policy_sha256"], EXPECTED_POLICY_SHA256)
        self.assertEqual(bindings["materialization_evidence_sha256"], EXPECTED_MATERIALIZATION_SHA256)
        self.assertEqual(self.baseline["metric_policy_id"], self.policy["policy_id"])
        self.assertEqual(self.baseline["corpus_id"], self.corpus["corpus_id"])

    def test_exact_40_cases_match_materialization_identity_and_have_finite_metrics(self):
        materialized = {case["id"]: case for case in self.materialization["cases"]}
        baseline_cases = self.baseline["cases"]
        self.assertEqual(self.baseline["case_count"], 40)
        self.assertEqual({case["id"] for case in baseline_cases}, set(materialized))
        for case in baseline_cases:
            source = materialized[case["id"]]
            self.assertEqual(case["clean_sha256"], source["clean_sha256"])
            self.assertEqual(case["noisy_sha256"], source["noisy_sha256"])
            self.assertEqual(case["frame_count"], source["frame_count"])
            self.assertEqual(case["sample_rate_hz"], 48000)
            si_sdr = float(case["metrics"]["si_sdr_db"])
            stoi = float(case["metrics"]["stoi"])
            self.assertTrue(math.isfinite(si_sdr))
            self.assertTrue(math.isfinite(stoi))
            self.assertGreaterEqual(stoi, 0.0)
            self.assertLessEqual(stoi, 1.0)

    def test_overall_summary_recomputes_from_all_cases_without_post_hoc_exclusion(self):
        cases = self.baseline["cases"]
        si = [float(case["metrics"]["si_sdr_db"]) for case in cases]
        stoi = [float(case["metrics"]["stoi"]) for case in cases]
        summary = self.baseline["summary"]["overall"]
        self.assertAlmostEqual(summary["si_sdr_db"]["mean"], statistics.fmean(si), places=7)
        self.assertAlmostEqual(summary["si_sdr_db"]["median"], statistics.median(si), places=7)
        self.assertEqual(summary["si_sdr_db"]["min"], min(si))
        self.assertEqual(summary["si_sdr_db"]["max"], max(si))
        self.assertAlmostEqual(summary["stoi"]["mean"], statistics.fmean(stoi), places=7)
        self.assertAlmostEqual(summary["stoi"]["median"], statistics.median(stoi), places=7)
        self.assertEqual(summary["stoi"]["min"], min(stoi))
        self.assertEqual(summary["stoi"]["max"], max(stoi))

    def test_baseline_is_descriptive_only_and_provenance_is_frozen(self):
        interpretation = self.baseline["interpretation"]
        self.assertTrue(interpretation["descriptive_noisy_baseline_only"])
        self.assertTrue(interpretation["objective_metrics_are_auxiliary_only"])
        self.assertFalse(interpretation["acceptance_thresholds_defined"])
        self.assertFalse(interpretation["algorithm_ranking_authorized"])
        self.assertFalse(interpretation["denoiser_selected"])
        self.assertFalse(interpretation["denoise_authorized"])
        self.assertFalse(interpretation["renderer_authorized"])
        self.assertTrue(interpretation["human_perceptual_comparison_required_before_treatment_authorization"])
        self.assertFalse(interpretation["auto_apply"])
        provenance = self.baseline["provenance"]
        self.assertEqual(provenance["workflow_run_id"], 34143456746)
        self.assertEqual(provenance["workflow_job_id"], 101810294783)
        self.assertEqual(provenance["workflow_artifact_id"], 10026834646)
        self.assertEqual(provenance["raw_baseline_manifest_sha256"], EXPECTED_RAW_BASELINE_SHA256)
        self.assertEqual(provenance["artifact_zip_sha256"], EXPECTED_ARTIFACT_ZIP_SHA256)


if __name__ == "__main__":
    unittest.main()
