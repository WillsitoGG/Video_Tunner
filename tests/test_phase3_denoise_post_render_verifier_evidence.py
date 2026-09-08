import json
import unittest
from pathlib import Path

from video_tunner.denoise_post_render_verification import (
    DENOISE_POST_RENDER_RECORD_TYPE,
    DENOISE_POST_RENDER_SCHEMA_VERSION,
    DENOISE_VERIFICATION_CHANNELS,
    DENOISE_VERIFICATION_SAMPLE_RATE_HZ,
)
from video_tunner.denoise_render import DENOISE_RENDER_AUDIO_CODEC
from video_tunner.denoise_runtime import DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "Validation" / "phase3-denoise-post-render-verifier-foundation.json"
PRECOMMIT = ROOT / "Validation" / "phase3-denoise-post-render-verifier-precommit.json"
WORKFLOW = ROOT / ".github" / "workflows" / "phase3-denoise-post-render-verifier.yml"


class Phase3DenoisePostRenderVerifierEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.precommit = json.loads(PRECOMMIT.read_text(encoding="utf-8"))

    def test_foundation_identity_and_validation_provenance_are_frozen(self):
        evidence = self.evidence
        self.assertEqual(evidence["schema_version"], 1)
        self.assertEqual(evidence["record_type"], "phase3_denoise_post_render_verifier_foundation")
        self.assertEqual(evidence["phase"], "3.6j")
        self.assertEqual(evidence["status"], "TECHNICAL_FOUNDATION_PASS")
        validation = evidence["validation"]
        self.assertEqual(validation["preflight_run_id"], 34241148527)
        self.assertEqual(validation["preflight_job_id"], 102111328370)
        self.assertEqual(validation["preflight_focused_tests"], "63/63 PASS")
        self.assertEqual(validation["run_id"], 34241518206)
        self.assertEqual(validation["job_id"], 102112597551)
        self.assertEqual(validation["head_sha"], "91bbe36d5c34ef864154240db5023cc8bbc4ff34")
        self.assertEqual(validation["focused_tests"], "63/63 PASS")
        self.assertEqual(validation["real_deepfilter_render_plus_independent_verifier_e2e"], "1/1 PASS")
        self.assertEqual(validation["integrated_tests"], "488/488 PASS")
        self.assertEqual(validation["integrated_skips"], 0)
        self.assertEqual(validation["doctor"], "PASS")
        self.assertTrue(validation["scope_note_pass"])

    def test_precommit_was_not_relaxed_after_results(self):
        self.assertEqual(self.precommit["status"], "PRECOMMITTED_BEFORE_IMPLEMENTATION")
        self.assertFalse(self.evidence["precommit"]["post_hoc_threshold_relaxation"])
        pre = self.precommit["technical_pass_contract"]
        contract = self.evidence["independent_verification_contract"]
        self.assertEqual(contract["output_audio_codec"], pre["output_audio_codec"])
        self.assertEqual(contract["output_audio_channels"], pre["output_audio_channels"])
        self.assertEqual(contract["output_audio_sample_rate_hz"], pre["output_audio_sample_rate_hz"])
        self.assertEqual(contract["raw_duration_delta_max_seconds"], pre["raw_duration_delta_max_seconds"])
        self.assertEqual(contract["allowed_timeline_normalization_actions"], pre["timeline_normalization_actions_allowed"])
        self.assertEqual(contract["alignment_search_allowed"], pre["alignment_search_allowed"])
        self.assertEqual(contract["time_shift_allowed"], pre["time_shift_allowed"])
        self.assertEqual(contract["level_matching_allowed"], pre["level_matching_allowed"])

    def test_persisted_contract_matches_implementation_constants(self):
        implementation = self.evidence["implementation"]
        contract = self.evidence["independent_verification_contract"]
        self.assertEqual(implementation["schema_version"], DENOISE_POST_RENDER_SCHEMA_VERSION)
        self.assertEqual(implementation["record_type"], DENOISE_POST_RENDER_RECORD_TYPE)
        self.assertEqual(contract["output_audio_codec"], DENOISE_RENDER_AUDIO_CODEC)
        self.assertEqual(contract["output_audio_channels"], DENOISE_VERIFICATION_CHANNELS)
        self.assertEqual(contract["output_audio_sample_rate_hz"], DENOISE_VERIFICATION_SAMPLE_RATE_HZ)
        self.assertEqual(contract["raw_duration_delta_max_seconds"], DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS)

    def test_synthetic_e2e_is_technical_only_and_exact(self):
        observed = self.evidence["synthetic_e2e_observation"]
        self.assertFalse(observed["real_user_media"])
        self.assertEqual(observed["status"], "technical_denoise_pass")
        self.assertTrue(observed["technical_pass"])
        self.assertEqual(observed["blockers"], [])
        self.assertTrue(observed["decoded_video_equal"])
        self.assertEqual(observed["source_decoded_audio_frames_48k_mono"], 144000)
        self.assertEqual(observed["output_decoded_audio_frames_48k_mono"], 144000)
        self.assertTrue(observed["human_perceptual_review_required"])
        self.assertFalse(observed["human_pass"])

    def test_no_objective_or_perceptual_threshold_was_added(self):
        contract = self.evidence["independent_verification_contract"]
        for key in (
            "snr_threshold_added",
            "stoi_threshold_added",
            "si_sdr_threshold_added",
            "loudness_threshold_added",
            "technical_pass_is_human_pass",
            "alignment_search_allowed",
            "time_shift_allowed",
            "level_matching_allowed",
            "auto_apply",
        ):
            self.assertFalse(contract[key])
        self.assertTrue(contract["human_perceptual_review_required_after_technical_pass"])
        self.assertEqual(contract["product_default"], "preserve")

    def test_actual_state_records_no_real_user_processing_or_human_closeout(self):
        state = self.evidence["actual_product_state"]
        self.assertTrue(state["independent_denoise_post_render_verifier_implemented"])
        self.assertTrue(state["independent_denoise_post_render_verifier_technical_foundation_pass"])
        self.assertFalse(state["real_user_authorization_record_created_in_3_6j"])
        self.assertFalse(state["real_user_media_authorized_for_denoise_in_3_6j"])
        self.assertFalse(state["real_user_media_processed_in_3_6j"])
        self.assertFalse(state["real_user_treated_media_generated_in_3_6j"])
        self.assertFalse(state["human_denoise_treatment_closeout_completed"])
        self.assertFalse(state["denoise_generalized_to_stereo_or_multichannel"])
        self.assertEqual(state["product_default"], "preserve")
        self.assertFalse(state["auto_apply"])
        self.assertEqual(self.evidence["interpretation"]["next_phase"], "3.6k_human_denoise_treatment_closeout")

    def test_permanent_gate_is_manual_only_and_includes_binder(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("tests.test_phase3_denoise_post_render_verifier_evidence", workflow)
        self.assertIn("No Guille media is processed or authorized", workflow)
        self.assertIn("Technical PASS remains distinct from human perceptual PASS", workflow)
        self.assertIn("No SNR/STOI/SI-SDR/loudness threshold is introduced", workflow)


if __name__ == "__main__":
    unittest.main()
