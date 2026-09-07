from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from video_tunner.denoise_selection import build_denoiser_selection_review


ROOT = Path(__file__).resolve().parents[1]
OBJECTIVE = ROOT / "Validation" / "phase3-denoiser-candidate-objective-comparison.json"
HUMAN = ROOT / "Validation" / "phase3-denoiser-human-perceptual-gate.json"
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_selection_policy_v1.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class DenoiseSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.objective = load(OBJECTIVE)
        self.human = load(HUMAN)
        self.policy = load(POLICY)

    def build(self):
        return build_denoiser_selection_review(
            objective_evidence=self.objective,
            human_gate=self.human,
            policy=self.policy,
        )

    def test_current_exact_evidence_selects_only_deepfilternet_for_integration_review(self):
        review = self.build()
        self.assertEqual(review["status"], "SELECTED_FOR_INTEGRATION_REVIEW")
        self.assertTrue(review["selection_completed"])
        self.assertEqual(review["human_eligible_candidates"], ["deepfilternet_0_5_6_compensated_v1"])
        self.assertEqual(review["selection_eligible_candidates"], ["deepfilternet_0_5_6_compensated_v1"])
        self.assertEqual(review["selected_candidate_id"], "deepfilternet_0_5_6_compensated_v1")
        evaluation = review["candidate_evaluations"][0]
        self.assertAlmostEqual(evaluation["mean_delta_vs_preserve"]["si_sdr_db"], 9.87013412, places=8)
        self.assertAlmostEqual(evaluation["mean_delta_vs_preserve"]["stoi"], 0.01112968, places=8)
        self.assertEqual(evaluation["positive_case_counts"]["si_sdr_db"], 40)
        self.assertEqual(evaluation["positive_case_counts"]["stoi"], 27)
        self.assertAlmostEqual(evaluation["clean_control_descriptive"]["stoi_mean"], 0.99542798, places=8)
        self.assertAlmostEqual(evaluation["clean_control_descriptive"]["normalized_rmse_mean"], 0.03238068, places=8)

    def test_afftdn_is_excluded_by_human_gate_before_objective_selection(self):
        review = self.build()
        self.assertNotIn("ffmpeg_afftdn_fixed_v1", review["human_eligible_candidates"])
        self.assertNotIn("ffmpeg_afftdn_fixed_v1", [x["candidate_id"] for x in review["candidate_evaluations"]])

    def test_tampered_human_gate_binding_fails_closed(self):
        self.human["review_fingerprint"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.build()

    def test_missing_or_duplicate_required_noisy_cases_fail_closed(self):
        candidate = self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]
        candidate["noisy_cases"].pop()
        with self.assertRaisesRegex(ValueError, "exactamente 40 noisy cases"):
            self.build()

        self.objective = load(OBJECTIVE)
        candidate = self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]
        candidate["noisy_cases"][-1] = copy.deepcopy(candidate["noisy_cases"][0])
        with self.assertRaisesRegex(ValueError, "duplicados"):
            self.build()

    def test_nonpositive_objective_aggregate_yields_no_selection_preserve_default(self):
        candidate = self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]
        for case in candidate["noisy_cases"]:
            case["delta_vs_preserve"]["stoi"] = -0.01
        candidate["noisy_summary"]["overall"]["delta_vs_preserve"]["stoi"]["mean"] = -0.01
        review = self.build()
        self.assertEqual(review["status"], "NO_SELECTION_PRESERVE_DEFAULT")
        self.assertIsNone(review["selected_candidate_id"])
        self.assertEqual(review["interpretation"]["product_default"], "preserve")

    def test_timeline_search_shift_level_or_excess_duration_fail_closed(self):
        candidate = self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]
        candidate["noisy_cases"][0]["timeline"]["alignment_search_performed"] = True
        with self.assertRaisesRegex(ValueError, "alignment_search_performed"):
            self.build()

        self.objective = load(OBJECTIVE)
        candidate = self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]
        candidate["noisy_cases"][0]["timeline"]["raw_duration_delta_seconds"] = -0.051
        with self.assertRaisesRegex(ValueError, "delta temporal"):
            self.build()

    def test_clean_control_is_required_but_no_post_hoc_numeric_acceptance_threshold_is_invented(self):
        candidate = self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]
        candidate["clean_control"]["summary"]["stoi"]["mean"] = 0.10
        candidate["clean_control"]["summary"]["normalized_rmse"]["mean"] = 9.0
        review = self.build()
        self.assertEqual(review["selected_candidate_id"], "deepfilternet_0_5_6_compensated_v1")
        descriptive = review["candidate_evaluations"][0]["clean_control_descriptive"]
        self.assertFalse(descriptive["numeric_acceptance_threshold_applied"])

        self.objective = load(OBJECTIVE)
        self.objective["results"]["deepfilternet_0_5_6_compensated_v1"]["clean_control"]["cases"].pop()
        with self.assertRaisesRegex(ValueError, "clean control debe contener 40"):
            self.build()

    def test_multiple_eligible_candidates_block_instead_of_auto_picking(self):
        source_id = "deepfilternet_0_5_6_compensated_v1"
        synthetic_id = "synthetic_second_human_and_objective_eligible_v1"
        synthetic = copy.deepcopy(self.objective["results"][source_id])
        synthetic["candidate"]["id"] = synthetic_id
        self.objective["results"][synthetic_id] = synthetic
        pair = copy.deepcopy(self.human["pair_results"][0])
        pair["pair_id"] = "synthetic_second_vs_preserve"
        pair["treatment_candidate_id"] = synthetic_id
        pair["public_pair_label"] = "synthetic_comparison"
        self.human["pair_results"].append(pair)

        review = self.build()
        self.assertFalse(review["selection_completed"])
        self.assertIsNone(review["selected_candidate_id"])
        self.assertEqual(review["status"], "BLOCKED_MULTIPLE_ELIGIBLE_REQUIRES_MANUAL_SELECTION")
        self.assertEqual(set(review["selection_eligible_candidates"]), {source_id, synthetic_id})

    def test_selection_never_authorizes_execution_or_changes_product_default(self):
        review = self.build()
        interpretation = review["interpretation"]
        self.assertTrue(interpretation["selected_candidate_is_for_integration_review_only"])
        self.assertEqual(interpretation["product_default"], "preserve")
        self.assertFalse(interpretation["product_default_changed"])
        self.assertFalse(interpretation["denoise_authorized"])
        self.assertFalse(interpretation["renderer_authorized"])
        self.assertFalse(interpretation["auto_apply"])


if __name__ == "__main__":
    unittest.main()
