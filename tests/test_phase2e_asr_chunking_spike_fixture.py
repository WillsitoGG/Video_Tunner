import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "tests" / "fixtures" / "phase2e_asr_chunking_spike_v1.json"
SOURCE = ROOT / "tests" / "fixtures" / "phase2e_human_render_closeout_ami_v1.json"


class Phase2EAsrChunkingSpikeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spike = json.loads(SPIKE.read_text(encoding="utf-8"))
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_locked_cases_match_existing_human_closeout_corpus(self):
        expected = [item["id"] for item in self.source["cases"]]
        self.assertEqual(self.spike["locked_case_ids"], expected)
        self.assertEqual(len(expected), 3)

    def test_profiles_are_precommitted_half_overlap_and_ordered_large_to_small(self):
        profiles = self.spike["profiles_in_preference_order"]
        self.assertEqual([item["id"] for item in profiles], ["w16_h8", "w12_h6", "w10_h5"])
        self.assertEqual([item["window_seconds"] for item in profiles], [16.0, 12.0, 10.0])
        for item in profiles:
            self.assertEqual(item["hop_seconds"], item["window_seconds"] / 2.0)
            self.assertEqual(item["overlap_fraction"], 0.5)

    def test_decoder_and_downstream_policy_remain_locked(self):
        settings = self.spike["locked_settings"]
        self.assertEqual(settings["model"], "large-v3-turbo")
        self.assertEqual(settings["language"], "en")
        self.assertEqual(settings["device"], "cpu")
        self.assertEqual(settings["compute_type"], "int8")
        self.assertTrue(settings["word_timestamps"])
        self.assertFalse(settings["vad_filter"])
        self.assertTrue(settings["condition_on_previous_text"])
        self.assertEqual(settings["semantic_mode"], "conservative")
        self.assertEqual(settings["human_timing_tolerance_seconds"], 0.75)
        self.assertEqual(settings["grid_origin_seconds"], 0.0)

    def test_profile_pass_requires_all_three_human_cases(self):
        policy = self.spike["success_policy"]
        self.assertEqual(policy["required_case_count"], 3)
        self.assertEqual(policy["required_recovered_human_cases"], 3)
        self.assertIn("fixed absolute grid from t=0", policy["profile_selection_rule"])
        self.assertIn("does not authorize a production transcription change", policy["note"])
        self.assertIn("5% removed-fraction limit", policy["note"])


if __name__ == "__main__":
    unittest.main()
