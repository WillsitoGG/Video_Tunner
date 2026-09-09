import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLOSEOUT = ROOT / "Validation" / "phase3-denoise-post-render-verifier-closeout.json"
FOUNDATION = ROOT / "Validation" / "phase3-denoise-post-render-verifier-foundation.json"
PRECOMMIT = ROOT / "Validation" / "phase3-denoise-post-render-verifier-precommit.json"
PERMANENT_GATE = ROOT / ".github" / "workflows" / "phase3-denoise-post-render-verifier.yml"
TEMP_PATHS = (
    ROOT / ".github" / "phase3-denoise-post-render-post-persistence.trigger",
    ROOT / ".github" / "workflows" / "phase3-denoise-post-render-post-persistence-once.yml",
    ROOT / ".github" / "phase3-6x-evidence-binder-sweep.trigger",
    ROOT / ".github" / "workflows" / "phase3-6x-evidence-binder-sweep-once.yml",
)


class Phase3DenoisePostRenderVerifierCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.closeout = json.loads(CLOSEOUT.read_text(encoding="utf-8"))
        cls.foundation = json.loads(FOUNDATION.read_text(encoding="utf-8"))
        cls.precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))

    def test_closeout_identity_and_final_validation_are_exact(self):
        closeout = self.closeout
        self.assertEqual(closeout["schema_version"], 1)
        self.assertEqual(closeout["record_type"], "phase3_denoise_post_render_verifier_closeout")
        self.assertEqual(closeout["phase"], "3.6j")
        self.assertEqual(closeout["status"], "TECHNICAL_FOUNDATION_CLOSED")
        final = closeout["validation"]["post_persistence_final"]
        self.assertEqual(final["run_id"], 34337071421)
        self.assertEqual(final["job_id"], 102418854722)
        self.assertEqual(final["head_sha"], "62973db54002d6fe6f379158b9c515c964a6502b")
        self.assertEqual(final["immutable_tools"], "PASS")
        self.assertEqual(final["focused_tests"], "71/71 PASS")
        self.assertEqual(final["real_deepfilter_render_plus_independent_verifier_e2e"], "1/1 PASS")
        self.assertEqual(final["integrated_tests"], "496/496 PASS")
        self.assertEqual(final["integrated_skips"], 0)
        self.assertEqual(final["doctor"], "PASS")
        self.assertEqual(final["scope_note"], "PASS")

    def test_base_foundation_remains_separate_and_unchanged_in_role(self):
        self.assertEqual(self.closeout["base_foundation_evidence"], "Validation/phase3-denoise-post-render-verifier-foundation.json")
        self.assertEqual(self.closeout["precommit_evidence"], "Validation/phase3-denoise-post-render-verifier-precommit.json")
        self.assertEqual(self.foundation["status"], "TECHNICAL_FOUNDATION_PASS")
        self.assertEqual(self.foundation["validation"]["run_id"], 34241518206)
        self.assertEqual(self.precommit["status"], "PRECOMMITTED_BEFORE_IMPLEMENTATION")
        self.assertFalse(self.closeout["contract_integrity"]["precommit_relaxed_after_results"])

    def test_post_persistence_e2e_is_technical_only(self):
        observed = self.closeout["post_persistence_e2e_observation"]
        self.assertEqual(observed["status"], "technical_denoise_pass")
        self.assertTrue(observed["technical_pass"])
        self.assertEqual(observed["blockers"], [])
        self.assertTrue(observed["decoded_video_equal"])
        self.assertEqual(observed["source_decoded_audio_frames_48k_mono"], 144000)
        self.assertEqual(observed["output_decoded_audio_frames_48k_mono"], 144000)
        self.assertTrue(observed["human_perceptual_review_required"])
        self.assertFalse(observed["human_pass"])
        self.assertFalse(observed["real_user_media"])

    def test_closeout_does_not_add_thresholds_or_user_authorization(self):
        integrity = self.closeout["contract_integrity"]
        for key in (
            "snr_threshold_added",
            "stoi_threshold_added",
            "si_sdr_threshold_added",
            "loudness_threshold_added",
            "technical_pass_is_human_pass",
            "auto_apply",
        ):
            self.assertFalse(integrity[key])
        self.assertEqual(integrity["product_default"], "preserve")
        state = self.closeout["actual_product_state"]
        self.assertTrue(state["independent_denoise_post_render_verifier_technical_foundation_closed"])
        self.assertFalse(state["real_user_authorization_record_created_in_3_6j"])
        self.assertFalse(state["real_user_media_authorized_for_denoise_in_3_6j"])
        self.assertFalse(state["real_user_media_processed_in_3_6j"])
        self.assertFalse(state["real_user_treated_media_generated_in_3_6j"])
        self.assertFalse(state["human_denoise_treatment_closeout_completed"])
        self.assertEqual(self.closeout["interpretation"]["next_phase"], "3.6k_human_denoise_treatment_closeout")

    def test_permanent_gate_is_manual_only_and_temporary_triggers_are_absent(self):
        workflow = PERMANENT_GATE.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        for path in TEMP_PATHS:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertFalse(path.exists())

    def test_release_and_validation_indexes_record_final_closeout(self):
        release = (ROOT / "RELEASE_STATUS.md").read_text(encoding="utf-8")
        validation = (ROOT / "Validation" / "README.md").read_text(encoding="utf-8")
        for text in (release, validation):
            self.assertIn("34337071421", text)
            self.assertIn("71/71", text)
            self.assertIn("496/496", text)
            self.assertIn("3.6k", text if text is release else "3.6k " + text)
        self.assertIn("phase3-denoise-post-render-verifier-closeout.json", validation)
        self.assertIn("Fase 3.6j post-persistence: **CLOSED", release)
        self.assertIn("human denoise treatment closeout", validation.lower())


if __name__ == "__main__":
    unittest.main()
