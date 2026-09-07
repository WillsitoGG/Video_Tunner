import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
METRICS = ROOT / "tests" / "fixtures" / "phase3_denoise_objective_metric_policy_v1.json"
BASELINE = ROOT / "Validation" / "phase3-denoise-objective-baseline.json"
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_candidate_comparison_policy_v1.json"

EXPECTED_CORPUS_SHA = "49e742ce7912d008ee5ef3cc3bd5a31b4c9f117125aa2a811b2a6bd00acb1c03"
EXPECTED_METRICS_SHA = "914e015140c933d201ca9e61d8d54c2a97579a44d748e8a5c3fb99c38da791b1"
EXPECTED_RAW_BASELINE_SHA = "0c11cf701618d461cd1144a817edc77f75225333b306f91310a972475cb183fe"
DF_SHA = "75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915"


class Phase3DenoiserCandidateComparisonPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    def test_bindings_are_exact_and_precommitted(self):
        bindings = self.policy["bindings"]
        self.assertEqual(hashlib.sha256(CORPUS.read_bytes()).hexdigest(), EXPECTED_CORPUS_SHA)
        self.assertEqual(hashlib.sha256(METRICS.read_bytes()).hexdigest(), EXPECTED_METRICS_SHA)
        self.assertEqual(bindings["corpus_fixture_sha256"], EXPECTED_CORPUS_SHA)
        self.assertEqual(bindings["objective_metric_policy_sha256"], EXPECTED_METRICS_SHA)
        self.assertEqual(bindings["raw_noisy_baseline_sha256"], EXPECTED_RAW_BASELINE_SHA)
        self.assertEqual(bindings["required_cases"], 40)
        self.assertEqual(self.baseline["provenance"]["raw_baseline_manifest_sha256"], EXPECTED_RAW_BASELINE_SHA)

    def test_candidate_set_is_exactly_control_afftdn_and_pinned_deepfilternet(self):
        candidates = {item["id"]: item for item in self.policy["candidates"]}
        self.assertEqual(
            set(candidates),
            {"preserve_noisy_control_v1", "ffmpeg_afftdn_fixed_v1", "deepfilternet_0_5_6_compensated_v1"},
        )
        self.assertFalse(candidates["preserve_noisy_control_v1"]["treatment"])
        self.assertEqual(
            candidates["ffmpeg_afftdn_fixed_v1"]["filter"],
            "afftdn=nr=12:nf=-50:nt=w:tn=0:tr=0",
        )
        df = candidates["deepfilternet_0_5_6_compensated_v1"]
        self.assertEqual(df["version"], "0.5.6")
        self.assertEqual(df["asset_sha256"], DF_SHA)
        self.assertEqual(df["asset_size_bytes"], 26912256)
        self.assertEqual(df["smoke_test_run_id"], 34144574712)
        self.assertEqual(df["smoke_test_output_seconds"], 2.97)
        self.assertFalse(df["explicit_model_argument"])

    def test_timeline_policy_forbids_post_hoc_alignment_optimization(self):
        media = self.policy["media_contract"]
        self.assertEqual(media["raw_duration_delta_max_seconds"], 0.05)
        normalization = media["metric_timeline_normalization"]
        self.assertEqual(normalization["method"], "right_pad_or_right_trim_only")
        self.assertFalse(normalization["alignment_search_allowed"])
        self.assertFalse(normalization["time_shift_allowed"])
        self.assertFalse(normalization["level_matching_allowed"])
        self.assertEqual(normalization["padding_value"], 0.0)

    def test_clean_controls_are_required_for_every_treatment_candidate(self):
        treatment = [item for item in self.policy["candidates"] if item["treatment"]]
        self.assertEqual(len(treatment), 2)
        self.assertTrue(all(item["clean_control_required"] for item in treatment))
        clean = self.policy["clean_preservation_evaluation"]
        self.assertTrue(clean["required_for_treatment_candidates"])
        self.assertEqual(clean["metrics"], ["stoi", "normalized_rmse"])
        self.assertFalse(clean["post_hoc_case_exclusion_allowed"])

    def test_objective_results_can_neither_select_nor_authorize_denoise(self):
        reporting = self.policy["reporting_policy"]
        self.assertTrue(reporting["descriptive_ordering_allowed"])
        self.assertFalse(reporting["winner_label_allowed"])
        self.assertFalse(reporting["acceptance_thresholds_defined"])
        self.assertFalse(reporting["candidate_selection_authorized"])
        self.assertFalse(reporting["denoiser_selected"])
        self.assertFalse(reporting["denoise_authorized"])
        self.assertFalse(reporting["renderer_authorized"])
        self.assertTrue(reporting["human_perceptual_ab_required_before_any_selection_or_authorization"])
        self.assertFalse(reporting["auto_apply"])


if __name__ == "__main__":
    unittest.main()
