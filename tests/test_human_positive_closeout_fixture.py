import json
import unittest
from pathlib import Path

from video_tunner.semantic_candidates import SEMANTIC_SETTINGS


FIXTURE = Path(__file__).parent / "fixtures" / "human_positive_closeout_ami_v1.json"


class HumanPositiveCloseoutFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_has_multiple_human_removable_labels(self):
        cases = self.fixture["cases"]
        self.assertGreaterEqual(len(cases), 3)
        self.assertTrue(all(case["human_label"] == "removable_reparandum" for case in cases))
        self.assertTrue(all(case["annotation_type"] == "repeat" for case in cases))
        self.assertEqual(self.fixture["license"], "CC BY 4.0")

    def test_long_cases_match_current_conservative_detector_floor(self):
        conservative_min = int(SEMANTIC_SETTINGS["conservative"]["min_repeat_tokens"])
        self.assertEqual(
            conservative_min,
            int(self.fixture["detector_contract"]["minimum_exact_repeat_tokens"]),
        )
        long_cases = [
            case
            for case in self.fixture["cases"]
            if case["detector_expectation"] == "long_detector_compatible"
        ]
        self.assertGreaterEqual(len(long_cases), 2)
        for case in long_cases:
            self.assertGreaterEqual(len(case["reparandum_word_ids"]), conservative_min)
            self.assertEqual(case["expected_candidate_kind"], "possible_repetition")

    def test_short_positive_is_explicit_known_limitation_not_negative_label(self):
        short_cases = [
            case
            for case in self.fixture["cases"]
            if case["detector_expectation"] == "short_known_limitation"
        ]
        self.assertGreaterEqual(len(short_cases), 1)
        for case in short_cases:
            self.assertLess(
                len(case["reparandum_word_ids"]),
                int(SEMANTIC_SETTINGS["conservative"]["min_repeat_tokens"]),
            )
            self.assertIsNone(case["expected_candidate_kind"])
            self.assertEqual(case["human_label"], "removable_reparandum")

    def test_manual_reparandum_and_reparans_are_same_repeat_text(self):
        for case in self.fixture["cases"]:
            left = " ".join(case["reparandum_text"].lower().split())
            right = " ".join(case["reparans_text"].lower().split())
            self.assertEqual(left, right, case["id"])
            self.assertLess(case["reparandum_start"], case["reparandum_end"])
            self.assertLessEqual(case["reparandum_end"], case["reparans_start"])
            self.assertLess(case["reparans_start"], case["reparans_end"])
            self.assertLessEqual(case["clip_start"], case["reparandum_start"])
            self.assertGreaterEqual(
                case["clip_start"] + case["clip_duration"],
                case["reparans_end"],
            )

    def test_cases_use_speaker_specific_individual_headsets(self):
        sources = self.fixture["audio_sources"]
        self.assertGreaterEqual(len(sources), 2)
        for case in self.fixture["cases"]:
            source_id = case["audio_source_id"]
            self.assertIn(source_id, sources)
            source = sources[source_id]
            self.assertEqual(source["meeting"], case["meeting"])
            self.assertEqual(source["speaker"], case["speaker"])
            self.assertEqual(source["source_kind"], "individual_headset")
            self.assertEqual(source["audio"], f'{case["meeting"]}.Headset-{source["channel"]}.wav')
            self.assertEqual(
                source["url"],
                "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/"
                f'{case["meeting"]}/audio/{source["audio"]}',
            )

    def test_pinned_annotation_provenance_records_channel_mapping_source(self):
        mirror = self.fixture["annotation_provenance"]["inspection_mirror"]
        self.assertEqual(mirror["repository"], "ColingPaper2018/DialogueAct-Tagger")
        self.assertEqual(
            mirror["commit"],
            "4307e9899ed9058e80d0861530de124d4f134317",
        )
        self.assertEqual(
            mirror["meeting_mapping"],
            "data/AMI/corpus/corpusResources/meetings.xml",
        )


if __name__ == "__main__":
    unittest.main()
