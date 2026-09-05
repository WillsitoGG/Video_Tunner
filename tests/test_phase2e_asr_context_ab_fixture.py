import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "tests" / "fixtures" / "phase2e_asr_context_ab_v1.json"
SOURCE = ROOT / "tests" / "fixtures" / "phase2e_human_render_closeout_ami_v1.json"


class Phase2EAsrContextABFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spike = json.loads(SPIKE.read_text(encoding="utf-8"))
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))

    def test_locked_cases_are_exactly_existing_human_closeout_cases(self):
        expected = [item["id"] for item in self.source["cases"]]
        self.assertEqual(self.spike["locked_case_ids"], expected)
        self.assertEqual(len(expected), 3)

    def test_only_whisper_previous_text_conditioning_differs_between_arms(self):
        arms = self.spike["arms"]
        self.assertTrue(arms["baseline"]["condition_on_previous_text"])
        self.assertFalse(arms["challenger"]["condition_on_previous_text"])
        settings = self.spike["locked_settings"]
        self.assertEqual(settings["model"], "large-v3-turbo")
        self.assertEqual(settings["language"], "en")
        self.assertEqual(settings["device"], "cpu")
        self.assertEqual(settings["compute_type"], "int8")
        self.assertTrue(settings["word_timestamps"])
        self.assertFalse(settings["vad_filter"])
        self.assertEqual(settings["semantic_mode"], "conservative")

    def test_success_is_all_or_nothing_and_not_a_product_authorization(self):
        policy = self.spike["success_policy"]
        self.assertEqual(policy["required_case_count"], 3)
        self.assertEqual(policy["required_challenger_long_exact_matches"], 3)
        self.assertEqual(policy["required_challenger_short_exact_matches"], 3)
        self.assertEqual(
            policy["decision_if_pass"],
            "CONDITIONING_OFF_CANDIDATE_FOR_FULL_PIPELINE_HARDENING",
        )
        self.assertIn("does not authorize a production switch", policy["note"])
        self.assertIn("5% removed-fraction limit", policy["note"])

    def test_source_fixture_keeps_real_context_window_rule(self):
        provenance = self.source["provenance"]
        self.assertEqual(provenance["render_context_before_seconds"], 20.0)
        self.assertEqual(provenance["render_context_after_seconds"], 20.0)
        for case in self.source["cases"]:
            self.assertLess(case["clip_duration"], 10.0)
            self.assertGreater(case["render_clip_duration"], 40.0)


if __name__ == "__main__":
    unittest.main()
