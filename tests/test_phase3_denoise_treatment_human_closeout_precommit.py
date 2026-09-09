import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRECOMMIT = ROOT / "Validation" / "phase3-denoise-treatment-human-closeout-precommit.json"
PHASE3E_POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_human_ab_policy_v1.json"
PHASE3E_CLOSEOUT = ROOT / "Validation" / "phase3-denoiser-human-perceptual-closeout.json"
SELECTION = ROOT / "Validation" / "phase3-denoiser-selection-review.json"
PHASE3J_CLOSEOUT = ROOT / "Validation" / "phase3-denoise-post-render-verifier-closeout.json"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


class Phase3DenoiseTreatmentHumanCloseoutPrecommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))
        cls.phase3e_policy = json.loads(PHASE3E_POLICY.read_text(encoding="utf-8"))
        cls.phase3e_closeout = json.loads(PHASE3E_CLOSEOUT.read_text(encoding="utf-8"))
        cls.selection = json.loads(SELECTION.read_text(encoding="utf-8"))
        cls.phase3j_closeout = json.loads(PHASE3J_CLOSEOUT.read_text(encoding="utf-8"))

    def test_precommit_identity_is_frozen_before_integrated_bundle(self):
        pre = self.precommit
        self.assertEqual(pre["schema_version"], 1)
        self.assertEqual(pre["record_type"], "phase3_denoise_treatment_human_closeout_precommit")
        self.assertEqual(pre["phase"], "3.6k")
        self.assertEqual(pre["status"], "PRECOMMITTED_BEFORE_INTEGRATED_LISTENING_BUNDLE")
        self.assertTrue(pre["case_selection"]["selection_frozen_before_3_6k_bundle_generation"])
        self.assertTrue(pre["human_closeout_gate"]["thresholds_frozen_before_3_6k_listening"])

    def test_exact_phase3e_case_set_and_order_are_reused_without_cherry_picking(self):
        selection = self.precommit["case_selection"]
        expected = self.phase3e_policy["case_selection"]["cases_in_selection_rank_order"]
        self.assertTrue(selection["selection_reuses_exact_phase3_6e_cases"])
        self.assertFalse(selection["objective_metric_values_used_for_3_6k_selection"])
        self.assertFalse(selection["phase3_6e_human_preferences_used_to_cherry_pick_cases"])
        self.assertFalse(selection["post_hoc_case_exclusion_allowed"])
        self.assertEqual(selection["required_cases"], 10)
        self.assertEqual(selection["cases_in_required_order"], expected)
        self.assertEqual(sum(float(case["snr_db"]) == 2.5 for case in expected), 5)
        self.assertEqual(sum(float(case["snr_db"]) == 17.5 for case in expected), 5)
        self.assertEqual(len({(case["speaker"], case["noise"]) for case in expected}), 10)

    def test_upstream_selection_and_technical_closeout_are_exact(self):
        bindings = self.precommit["upstream_bindings"]
        self.assertEqual(sha256_path(PHASE3E_POLICY), bindings["case_selection_policy_sha256"])
        self.assertEqual(self.phase3e_closeout["status"], bindings["phase3_6e_closeout_status_required"])
        self.assertEqual(self.selection["status"], bindings["phase3_6f_selection_status_required"])
        self.assertEqual(self.selection["selected_candidate_id"], bindings["selected_candidate_id"])
        self.assertEqual(self.phase3j_closeout["status"], bindings["phase3_6j_status_required"])
        self.assertEqual(
            self.phase3j_closeout["validation"]["post_persistence_final"]["run_id"],
            bindings["phase3_6j_post_persistence_run_id"],
        )

    def test_blinding_mapping_is_rederived_and_balanced(self):
        blind = self.precommit["blinding_contract"]
        case_ids = [case["id"] for case in self.precommit["case_selection"]["cases_in_required_order"]]
        ranked = sorted(
            case_ids,
            key=lambda case_id: hashlib.sha256(
                f"{blind['blinding_seed']}|{case_id}".encode("utf-8")
            ).hexdigest(),
        )
        expected_a = set(ranked[:5])
        labels = blind["treatment_label_by_case"]
        self.assertTrue(blind["blind_before_human_review"])
        self.assertFalse(blind["public_bundle_exposes_treatment_identity"])
        self.assertFalse(blind["public_bundle_exposes_treatment_label_mapping"])
        self.assertEqual(set(labels), set(case_ids))
        self.assertEqual({case_id for case_id, label in labels.items() if label == "A"}, expected_a)
        self.assertEqual(sum(label == "A" for label in labels.values()), 5)
        self.assertEqual(sum(label == "B" for label in labels.values()), 5)
        self.assertEqual(blind["required_treatment_as_a"], 5)
        self.assertEqual(blind["required_treatment_as_b"], 5)

    def test_integrated_fixture_requires_full_renderer_and_verifier_chain_before_listening(self):
        fixture = self.precommit["integrated_fixture_contract"]
        self.assertFalse(fixture["real_user_media"])
        self.assertTrue(fixture["dataset_media_only"])
        self.assertFalse(fixture["authorization"]["counts_as_real_guille_authorization"])
        self.assertEqual(
            fixture["required_execution_chain"],
            [
                "denoise_plan_proposal",
                "denoise_execution_authorization",
                "denoise_render_result",
                "denoise_post_render_verification",
            ],
        )
        technical = fixture["technical_precondition"]
        self.assertEqual(technical["required_technical_verifications"], 10)
        self.assertEqual(technical["required_technical_passes"], 10)
        self.assertEqual(technical["allowed_technical_failures"], 0)
        self.assertEqual(technical["allowed_invalid_or_stale_evidence"], 0)
        self.assertEqual(technical["bundle_generation_on_any_technical_failure"], "BLOCK")
        self.assertTrue(technical["human_review_must_not_start_until_all_technical_cases_pass"])

    def test_listening_media_forbids_post_hoc_alignment_or_loudness_changes(self):
        media = self.precommit["listening_media_contract"]
        self.assertEqual(media["sample_rate_hz"], 48000)
        self.assertEqual(media["channels"], 1)
        self.assertEqual(media["codec"], "pcm_s16le")
        self.assertFalse(media["post_decode_alignment_search_allowed"])
        self.assertFalse(media["post_decode_time_shift_allowed"])
        self.assertFalse(media["level_matching_allowed"])
        self.assertFalse(media["loudness_normalization_allowed"])
        self.assertFalse(media["post_hoc_trimming_allowed"])
        self.assertFalse(media["post_hoc_case_exclusion_allowed"])
        self.assertIn("same integrated MP4 container path", media["reason_for_source_decoded_preserve"])

    def test_human_gate_reuses_phase3e_threshold_instead_of_inventing_new_one(self):
        old = self.phase3e_policy["per_treatment_advancement_gate"]
        new = self.precommit["human_closeout_gate"]
        self.assertIn("exact reuse", new["threshold_source"])
        self.assertEqual(new["required_reviews"], old["required_reviews"])
        self.assertEqual(new["minimum_integrated_treatment_preferences"], old["minimum_treatment_preferences"])
        self.assertEqual(
            new["maximum_integrated_treatment_speech_integrity_failures"],
            old["maximum_treatment_speech_integrity_failures"],
        )
        self.assertEqual(
            new["maximum_integrated_treatment_artifact_failures"],
            old["maximum_treatment_artifact_failures"],
        )
        self.assertEqual(new["minimum_integrated_treatment_preferences"], 7)
        self.assertEqual(new["maximum_integrated_treatment_speech_integrity_failures"], 0)
        self.assertEqual(new["maximum_integrated_treatment_artifact_failures"], 0)
        self.assertFalse(new["ties_count_as_treatment_preferences"])
        self.assertTrue(new["all_technical_cases_must_pass"])
        self.assertEqual(new["pass_status"], "HUMAN_TREATMENT_CLOSEOUT_READY")
        self.assertEqual(new["fail_status"], "INSUFFICIENT_INTEGRATED_TREATMENT_QUALITY")
        self.assertEqual(new["invalid_or_stale_status"], "INVALID_EVIDENCE")
        self.assertEqual(new["incomplete_human_status"], "PENDING_HUMAN_REVIEW")

    def test_review_form_and_capabilities_cannot_smuggle_product_authorization(self):
        review = self.precommit["human_review_form"]
        self.assertEqual(review["required_reviews"], 10)
        self.assertEqual(review["preference_values"], ["A", "B", "NO_PREFERENCE"])
        self.assertEqual(review["per_clip_speech_integrity_values"], ["PASS", "FAIL"])
        self.assertEqual(review["per_clip_artifact_values"], ["PASS", "FAIL"])
        self.assertTrue(review["reason_required"])
        caps = self.precommit["capability_boundaries"]
        self.assertFalse(caps["human_review_can_create_real_guille_authorization"])
        self.assertFalse(caps["human_review_can_change_product_default"])
        self.assertFalse(caps["human_review_can_enable_auto_apply"])
        self.assertFalse(caps["human_review_can_generalize_stereo_or_multichannel"])
        self.assertFalse(caps["real_guille_media_authorized"])
        self.assertFalse(caps["real_guille_media_processed"])
        self.assertEqual(caps["product_default"], "preserve")
        self.assertFalse(caps["auto_apply"])


if __name__ == "__main__":
    unittest.main()
