import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
POLICY_PATH = ROOT / "tests" / "fixtures" / "phase3_denoiser_human_ab_policy_v1.json"


class Phase3DenoiserHumanABPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.corpus_by_cell = {
            (case["speaker"], case["noise"], float(case["snr_db"])): case["id"]
            for case in cls.corpus["cases"]
        }

    def test_case_selection_is_exactly_rederived_without_objective_metrics(self):
        selection = self.policy["case_selection"]
        self.assertTrue(selection["selection_frozen_before_human_listening"])
        self.assertFalse(selection["objective_metric_values_used_for_case_selection"])
        self.assertFalse(selection["human_preferences_used_for_case_selection"])
        self.assertEqual(selection["required_cases"], 10)

        seed = selection["algorithm"]["seed"]
        cells = [(speaker, noise) for speaker in selection["speakers"] for noise in selection["noise_types"]]
        ranked = sorted(
            cells,
            key=lambda cell: hashlib.sha256(f"{seed}|{cell[0]}|{cell[1]}".encode("utf-8")).hexdigest(),
        )
        expected = []
        for index, (speaker, noise) in enumerate(ranked):
            snr = 2.5 if index < 5 else 17.5
            expected.append(
                {
                    "id": self.corpus_by_cell[(speaker, noise, snr)],
                    "speaker": speaker,
                    "noise": noise,
                    "snr_db": snr,
                }
            )
        self.assertEqual(selection["cases_in_selection_rank_order"], expected)
        self.assertEqual(sum(case["snr_db"] == 2.5 for case in expected), 5)
        self.assertEqual(sum(case["snr_db"] == 17.5 for case in expected), 5)
        self.assertEqual({(case["speaker"], case["noise"]) for case in expected}, set(cells))

    def test_pairwise_blinding_is_balanced_and_rederived_from_fixed_seeds(self):
        selected = [case["id"] for case in self.policy["case_selection"]["cases_in_selection_rank_order"]]
        self.assertEqual(len(self.policy["pairwise_comparisons"]), 2)
        for pair in self.policy["pairwise_comparisons"]:
            ranked = sorted(
                selected,
                key=lambda case_id: hashlib.sha256(
                    f"{pair['blinding_seed']}|{case_id}".encode("utf-8")
                ).hexdigest(),
            )
            expected_a = set(ranked[:5])
            labels = pair["treatment_label_by_case"]
            self.assertEqual(set(labels), set(selected))
            self.assertEqual({case_id for case_id, label in labels.items() if label == "A"}, expected_a)
            self.assertEqual(sum(label == "A" for label in labels.values()), 5)
            self.assertEqual(sum(label == "B" for label in labels.values()), 5)
            self.assertEqual(pair["required_treatment_as_a"], 5)
            self.assertEqual(pair["required_treatment_as_b"], 5)

    def test_exact_treatments_are_preserve_vs_both_objective_candidates(self):
        pairs = {pair["pair_id"]: pair for pair in self.policy["pairwise_comparisons"]}
        self.assertEqual(set(pairs), {"deepfilternet_vs_preserve", "afftdn_vs_preserve"})
        self.assertEqual(pairs["deepfilternet_vs_preserve"]["treatment_candidate_id"], "deepfilternet_0_5_6_compensated_v1")
        self.assertEqual(pairs["afftdn_vs_preserve"]["treatment_candidate_id"], "ffmpeg_afftdn_fixed_v1")
        for pair in pairs.values():
            self.assertEqual(pair["control_candidate_id"], "preserve_noisy_control_v1")

    def test_public_bundle_contract_hides_pair_and_treatment_identity(self):
        blind = self.policy["blinding_contract"]
        self.assertFalse(blind["public_bundle_exposes_candidate_names"])
        self.assertFalse(blind["public_bundle_exposes_treatment_label_mapping"])
        self.assertEqual(blind["public_bundle_pair_labels"], ["comparison_1", "comparison_2"])
        self.assertTrue(blind["blinding_key_stays_in_repository_policy_until_human_decisions_are_complete"])
        public_labels = [pair["public_pair_label"] for pair in self.policy["pairwise_comparisons"]]
        self.assertEqual(public_labels, ["comparison_1", "comparison_2"])
        self.assertEqual(len(set(public_labels)), 2)

    def test_listening_media_contract_forbids_metric_or_timeline_optimization(self):
        media = self.policy["listening_media_contract"]
        self.assertEqual(media["sample_rate_hz"], 48000)
        self.assertEqual(media["channels"], 1)
        self.assertEqual(media["codec"], "pcm_s16le")
        self.assertTrue(media["clean_reference_included_once_per_case"])
        self.assertIn("not a selectable candidate", media["clean_reference_purpose"])
        self.assertEqual(media["deepfilternet_raw_duration_delta_max_seconds"], 0.05)
        self.assertTrue(media["right_tail_normalization_only"])
        self.assertFalse(media["alignment_search_allowed"])
        self.assertFalse(media["time_shift_allowed"])
        self.assertFalse(media["level_matching_allowed"])
        self.assertFalse(media["loudness_normalization_allowed"])
        self.assertFalse(media["post_hoc_case_exclusion_allowed"])

    def test_human_gate_thresholds_are_precommitted_and_conservative(self):
        review = self.policy["review_form"]
        gate = self.policy["per_treatment_advancement_gate"]
        self.assertEqual(review["required_reviewed_pairs"], 20)
        self.assertEqual(review["preference_values"], ["A", "B", "NO_PREFERENCE"])
        self.assertEqual(review["per_clip_speech_integrity_values"], ["PASS", "FAIL"])
        self.assertEqual(review["per_clip_artifact_values"], ["PASS", "FAIL"])
        self.assertTrue(review["reason_required"])
        self.assertTrue(gate["evaluated_separately_for_each_pair_id"])
        self.assertEqual(gate["required_reviews"], 10)
        self.assertEqual(gate["minimum_treatment_preferences"], 7)
        self.assertFalse(gate["ties_count_as_treatment_preferences"])
        self.assertEqual(gate["maximum_treatment_speech_integrity_failures"], 0)
        self.assertEqual(gate["maximum_treatment_artifact_failures"], 0)
        self.assertTrue(gate["thresholds_frozen_before_human_listening"])
        self.assertEqual(gate["gate_pass_meaning"], "eligible_for_later_candidate_selection_review_only")

    def test_human_review_still_has_zero_product_execution_capability(self):
        caps = self.policy["capabilities"]
        self.assertFalse(caps["human_review_can_choose_product_default"])
        self.assertFalse(caps["candidate_selection_authorized"])
        self.assertFalse(caps["denoiser_selected"])
        self.assertFalse(caps["denoise_authorized"])
        self.assertFalse(caps["renderer_authorized"])
        self.assertFalse(caps["auto_apply"])
        self.assertTrue(caps["preserve_remains_product_default_until_separate_authorized_selection_work"])


if __name__ == "__main__":
    unittest.main()
