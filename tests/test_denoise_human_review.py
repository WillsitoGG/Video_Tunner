import copy
import json
import unittest
from pathlib import Path

from video_tunner.denoise_human_review import (
    build_pending_review_template,
    build_perceptual_gate,
    remap_public_review_to_private,
    validate_completed_review,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "tests" / "fixtures" / "phase3_denoiser_human_ab_policy_v1.json"
POLICY_SHA = "policy-sha-for-unit-test"
MANIFEST_SHA = "manifest-sha-for-unit-test"


class DenoiseHumanReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def completed_private_review(self):
        review = build_pending_review_template(
            policy=self.policy,
            policy_sha256=POLICY_SHA,
            bundle_manifest_sha256=MANIFEST_SHA,
        )
        review["reviewer"] = "human-reviewer"
        review["status"] = "COMPLETE"
        pair_by_public = {pair["public_pair_label"]: pair for pair in self.policy["pairwise_comparisons"]}
        for decision in review["decisions"]:
            pair = pair_by_public[decision["comparison"]]
            decision["preference"] = pair["treatment_label_by_case"][decision["case_id"]]
            decision["A"] = {"speech_integrity": "PASS", "artifact": "PASS"}
            decision["B"] = {"speech_integrity": "PASS", "artifact": "PASS"}
            decision["reason"] = "Audición comparativa completada."
        return review

    def test_pending_template_is_exactly_20_non_executable_private_decisions(self):
        review = build_pending_review_template(
            policy=self.policy,
            policy_sha256=POLICY_SHA,
            bundle_manifest_sha256=MANIFEST_SHA,
        )
        self.assertEqual(len(review["decisions"]), 20)
        expected_cases = {case["id"] for case in self.policy["case_selection"]["cases_in_selection_rank_order"]}
        self.assertEqual({item["case_id"] for item in review["decisions"]}, expected_cases)
        self.assertEqual({item["comparison"] for item in review["decisions"]}, {"comparison_1", "comparison_2"})
        self.assertFalse(any(review["capabilities"].values()))

    def test_public_case_labels_remap_exactly_without_changing_judgments(self):
        private = self.completed_private_review()
        public = copy.deepcopy(private)
        private_to_public = {
            case["id"]: f"case_{index:02d}"
            for index, case in enumerate(self.policy["case_selection"]["cases_in_selection_rank_order"], start=1)
        }
        for decision in public["decisions"]:
            decision["case_id"] = private_to_public[decision["case_id"]]
        public["note"] = "public bundle note"

        remapped = remap_public_review_to_private(public_review=public, policy=self.policy)
        self.assertNotIn("note", remapped)
        self.assertEqual(remapped["decisions"], private["decisions"])
        validate_completed_review(
            review=remapped,
            policy=self.policy,
            expected_policy_sha256=POLICY_SHA,
            expected_bundle_manifest_sha256=MANIFEST_SHA,
        )

    def test_public_remap_fails_closed_on_unknown_or_duplicate_case(self):
        private = self.completed_private_review()
        public = copy.deepcopy(private)
        private_to_public = {
            case["id"]: f"case_{index:02d}"
            for index, case in enumerate(self.policy["case_selection"]["cases_in_selection_rank_order"], start=1)
        }
        for decision in public["decisions"]:
            decision["case_id"] = private_to_public[decision["case_id"]]
        public["decisions"][0]["case_id"] = "case_99"
        with self.assertRaises(ValueError):
            remap_public_review_to_private(public_review=public, policy=self.policy)

        public = copy.deepcopy(private)
        for decision in public["decisions"]:
            decision["case_id"] = private_to_public[decision["case_id"]]
        public["decisions"][1] = copy.deepcopy(public["decisions"][0])
        with self.assertRaises(ValueError):
            remap_public_review_to_private(public_review=public, policy=self.policy)

    def test_all_treatment_preferences_pass_both_advancement_gates_without_authorization(self):
        review = self.completed_private_review()
        gate = build_perceptual_gate(
            review=review,
            policy=self.policy,
            expected_policy_sha256=POLICY_SHA,
            expected_bundle_manifest_sha256=MANIFEST_SHA,
        )
        self.assertEqual(len(gate["pair_results"]), 2)
        for result in gate["pair_results"]:
            self.assertEqual(result["treatment_preferences"], 10)
            self.assertEqual(result["treatment_speech_integrity_failures"], 0)
            self.assertEqual(result["treatment_artifact_failures"], 0)
            self.assertTrue(result["perceptual_gate_pass"])
            self.assertEqual(result["status"], "ELIGIBLE_FOR_SELECTION_REVIEW")
        interpretation = gate["interpretation"]
        self.assertFalse(interpretation["candidate_selection_authorized"])
        self.assertFalse(interpretation["denoiser_selected"])
        self.assertFalse(interpretation["denoise_authorized"])
        self.assertFalse(interpretation["renderer_authorized"])
        self.assertFalse(interpretation["auto_apply"])
        self.assertTrue(interpretation["preserve_remains_product_default"])

    def test_one_treatment_artifact_failure_blocks_only_that_pair(self):
        review = self.completed_private_review()
        target_pair = self.policy["pairwise_comparisons"][0]
        case_id = self.policy["case_selection"]["cases_in_selection_rank_order"][0]["id"]
        treatment_label = target_pair["treatment_label_by_case"][case_id]
        decision = next(
            item for item in review["decisions"]
            if item["case_id"] == case_id and item["comparison"] == target_pair["public_pair_label"]
        )
        decision[treatment_label]["artifact"] = "FAIL"
        decision["reason"] = "Artefacto audible en la versión preferida."

        gate = build_perceptual_gate(
            review=review,
            policy=self.policy,
            expected_policy_sha256=POLICY_SHA,
            expected_bundle_manifest_sha256=MANIFEST_SHA,
        )
        by_pair = {item["pair_id"]: item for item in gate["pair_results"]}
        self.assertFalse(by_pair[target_pair["pair_id"]]["perceptual_gate_pass"])
        self.assertEqual(by_pair[target_pair["pair_id"]]["status"], "NOT_ADVANCED_PRESERVE_DEFAULT")
        other_pair = self.policy["pairwise_comparisons"][1]["pair_id"]
        self.assertTrue(by_pair[other_pair]["perceptual_gate_pass"])

    def test_capability_tampering_is_rejected(self):
        review = self.completed_private_review()
        review["capabilities"]["denoise_authorized"] = True
        with self.assertRaises(ValueError):
            validate_completed_review(
                review=review,
                policy=self.policy,
                expected_policy_sha256=POLICY_SHA,
                expected_bundle_manifest_sha256=MANIFEST_SHA,
            )


if __name__ == "__main__":
    unittest.main()
