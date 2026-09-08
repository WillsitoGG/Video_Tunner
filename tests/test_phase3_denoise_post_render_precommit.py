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
PRECOMMIT = ROOT / "Validation" / "phase3-denoise-post-render-verifier-precommit.json"


class Phase3DenoisePostRenderPrecommitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(PRECOMMIT.read_text(encoding="utf-8"))

    def test_precommit_identity_is_frozen_before_verifier_closeout(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["record_type"], "phase3_denoise_post_render_verifier_precommit")
        self.assertEqual(self.record["phase"], "3.6j")
        self.assertEqual(self.record["status"], "PRECOMMITTED_BEFORE_IMPLEMENTATION")

    def test_technical_contract_matches_implementation_constants(self):
        contract = self.record["technical_pass_contract"]
        self.assertEqual(contract["output_audio_codec"], DENOISE_RENDER_AUDIO_CODEC)
        self.assertEqual(contract["output_audio_channels"], DENOISE_VERIFICATION_CHANNELS)
        self.assertEqual(contract["output_audio_sample_rate_hz"], DENOISE_VERIFICATION_SAMPLE_RATE_HZ)
        self.assertEqual(
            contract["raw_duration_delta_max_seconds"],
            DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
        )
        self.assertEqual(
            contract["timeline_normalization_actions_allowed"],
            ["none", "trim_right_tail", "pad_right_tail_silence"],
        )
        self.assertFalse(contract["alignment_search_allowed"])
        self.assertFalse(contract["time_shift_allowed"])
        self.assertFalse(contract["level_matching_allowed"])
        self.assertFalse(contract["source_overwrite_allowed"])

    def test_no_post_hoc_objective_or_perceptual_thresholds_exist(self):
        non_goals = self.record["explicit_non_goals"]
        for key in (
            "no_snr_threshold",
            "no_stoi_threshold",
            "no_si_sdr_threshold",
            "no_loudness_threshold",
            "no_perceptual_quality_claim",
            "technical_pass_does_not_equal_human_pass",
            "technical_pass_does_not_authorize_other_media",
        ):
            self.assertTrue(non_goals[key])
        self.assertEqual(non_goals["product_default"], "preserve")
        self.assertFalse(non_goals["auto_apply"])

    def test_closeout_boundary_is_technical_only(self):
        closeout = self.record["closeout_rule"]
        self.assertTrue(closeout["technical_pass_requires_zero_technical_blockers"])
        self.assertTrue(closeout["human_perceptual_review_remains_required_after_technical_pass"])
        self.assertFalse(closeout["real_user_media_processed_in_3_6j_foundation"])
        self.assertEqual(DENOISE_POST_RENDER_SCHEMA_VERSION, 1)
        self.assertEqual(DENOISE_POST_RENDER_RECORD_TYPE, "denoise_post_render_verification")


if __name__ == "__main__":
    unittest.main()
