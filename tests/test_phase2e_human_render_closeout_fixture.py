import json
import unittest
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "phase2e_human_render_closeout_ami_v1.json"
EXPECTED_CASE_IDS = {
    "ami-es2002b-d-repeat-157",
    "ami-ts3005d-c-repeat-298",
    "ami-es2002b-d-repeat-13",
}
EXPECTED_SOURCES = {"ES2002b-D", "TS3005d-C"}


class Phase2EHumanRenderCloseoutFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_corpus_is_exactly_the_preexisting_phase2d6_foundation_set(self):
        self.assertEqual(self.spec["schema_version"], 1)
        cases = self.spec["cases"]
        self.assertEqual(len(cases), 3)
        self.assertEqual({case["id"] for case in cases}, EXPECTED_CASE_IDS)
        self.assertTrue(all(case["expected_phase2d6_status"] == "foundation_guards_pass" for case in cases))
        self.assertTrue(all(case["human_label"] == "removable_reparandum" for case in cases))
        self.assertTrue(all(case["expected_candidate_kind"] == "possible_repetition" for case in cases))

    def test_closeout_thresholds_are_precommitted_and_all_or_nothing(self):
        policy = self.spec["closeout_policy"]
        self.assertEqual(policy["minimum_rendered_human_cases"], 3)
        self.assertEqual(policy["minimum_distinct_audio_sources"], 2)
        self.assertEqual(policy["required_technical_pass_fraction"], 1.0)
        self.assertEqual(policy["required_human_perceptual_pass_fraction"], 1.0)
        self.assertEqual(policy["maximum_safety_violations"], 0)
        self.assertEqual(policy["decision_if_all_pass"], "CLOSE_OUT_READY")
        self.assertEqual(policy["decision_if_any_fail"], "INSUFFICIENT_JOIN_QUALITY")

    def test_audio_sources_are_speaker_specific_and_pinned(self):
        sources = self.spec["audio_sources"]
        self.assertEqual(set(sources), EXPECTED_SOURCES)
        for source in sources.values():
            self.assertEqual(source["source_kind"], "individual_headset")
            self.assertGreater(int(source["expected_bytes"]), 1_000_000)
            digest = str(source["expected_sha256"])
            self.assertEqual(len(digest), 64)
            self.assertTrue(all(ch in "0123456789ABCDEF" for ch in digest))

    def test_every_case_has_valid_clip_and_manual_span(self):
        for case in self.spec["cases"]:
            clip_start = float(case["clip_start"])
            clip_duration = float(case["clip_duration"])
            manual_start = float(case["reparandum_start"])
            manual_end = float(case["reparandum_end"])
            self.assertGreater(clip_duration, 5.0)
            self.assertGreater(manual_end, manual_start)
            self.assertGreaterEqual(manual_start, clip_start)
            self.assertLessEqual(manual_end, clip_start + clip_duration)
            self.assertIn(case["audio_source_id"], EXPECTED_SOURCES)


if __name__ == "__main__":
    unittest.main()
