import json
import unittest
from pathlib import Path

from video_tunner.semantic_candidates import SEMANTIC_SETTINGS, _normalise


FIXTURE_V1 = Path(__file__).parent / "fixtures" / "human_positive_closeout_ami_v1.json"
FIXTURE_V2 = Path(__file__).parent / "fixtures" / "human_positive_closeout_ami_v2.json"


def production_tokens(text: str) -> list[str]:
    return [token for token in (_normalise(raw) for raw in text.split()) if token]


class HumanPositiveCloseoutFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_v1 = json.loads(FIXTURE_V1.read_text(encoding="utf-8"))
        cls.fixture_v2 = json.loads(FIXTURE_V2.read_text(encoding="utf-8"))

    def test_v1_preserves_original_short_limitation_control(self):
        cases = self.fixture_v1["cases"]
        short_cases = [
            case
            for case in cases
            if case["detector_expectation"] == "short_known_limitation"
        ]
        self.assertGreaterEqual(len(short_cases), 1)
        for case in short_cases:
            self.assertLess(
                len(production_tokens(case["reparandum_text"])),
                int(SEMANTIC_SETTINGS["conservative"]["min_repeat_tokens"]),
            )
            self.assertIsNone(case["expected_candidate_kind"])
            self.assertEqual(case["human_label"], "removable_reparandum")

    def test_v2_is_reproducible_expanded_exact_repeat_selection(self):
        fixture = self.fixture_v2
        self.assertEqual(fixture["schema_version"], 2)
        self.assertEqual(fixture["license"], "CC BY 4.0")
        selection = fixture["annotation_provenance"]["selection"]
        self.assertEqual(selection["discovery_run"], 33892213960)
        self.assertEqual(selection["discovered_exact_repeat_cases"], 80)
        self.assertEqual(selection["selected_cases"], 8)
        self.assertEqual(selection["selected_sources"], 4)
        self.assertEqual(len(fixture["cases"]), 8)
        self.assertEqual(len(fixture["audio_sources"]), 4)

    def test_v2_matches_current_conservative_detector_floor_exactly(self):
        fixture = self.fixture_v2
        conservative_min = int(SEMANTIC_SETTINGS["conservative"]["min_repeat_tokens"])
        self.assertEqual(
            conservative_min,
            int(fixture["detector_contract"]["minimum_exact_repeat_tokens"]),
        )
        for case in fixture["cases"]:
            self.assertEqual(case["detector_expectation"], "long_detector_compatible")
            self.assertEqual(case["expected_candidate_kind"], "possible_repetition")
            reparandum_tokens = production_tokens(case["reparandum_text"])
            reparans_tokens = production_tokens(case["reparans_text"])
            self.assertEqual(reparandum_tokens, reparans_tokens, case["id"])
            self.assertEqual(len(reparandum_tokens), case["token_count"], case["id"])
            self.assertGreaterEqual(case["token_count"], conservative_min)

    def test_v2_contractions_are_single_production_tokens(self):
        case = next(
            case
            for case in self.fixture_v2["cases"]
            if case["id"] == "ami-es2002b-d-repeat-157"
        )
        tokens = production_tokens(case["reparandum_text"])
        self.assertEqual(tokens, ["what", "youve", "just", "told", "me"])
        self.assertEqual(case["token_count"], 5)

    def test_v2_manual_spans_and_clip_bounds_are_valid(self):
        for case in self.fixture_v2["cases"]:
            self.assertEqual(case["human_label"], "removable_reparandum")
            self.assertEqual(case["annotation_type"], "repeat")
            self.assertLess(case["reparandum_start"], case["reparandum_end"])
            self.assertLessEqual(case["reparandum_end"], case["reparans_start"])
            self.assertLess(case["reparans_start"], case["reparans_end"])
            self.assertLessEqual(case["clip_start"], case["reparandum_start"])
            self.assertGreaterEqual(
                case["clip_start"] + case["clip_duration"],
                case["reparans_end"],
            )

    def test_v2_cases_use_speaker_specific_individual_headsets(self):
        sources = self.fixture_v2["audio_sources"]
        per_source: dict[str, int] = {}
        for case in self.fixture_v2["cases"]:
            source_id = case["audio_source_id"]
            self.assertIn(source_id, sources)
            source = sources[source_id]
            self.assertEqual(source["meeting"], case["meeting"])
            self.assertEqual(source["speaker"], case["speaker"])
            self.assertEqual(source["channel"], case["channel"])
            self.assertEqual(source["source_kind"], "individual_headset")
            self.assertEqual(
                source["audio"],
                f'{case["meeting"]}.Headset-{source["channel"]}.wav',
            )
            self.assertEqual(
                source["url"],
                "https://groups.inf.ed.ac.uk/ami/AMICorpusMirror/amicorpus/"
                f'{case["meeting"]}/audio/{source["audio"]}',
            )
            per_source[source_id] = per_source.get(source_id, 0) + 1
        self.assertTrue(all(count <= 2 for count in per_source.values()))

    def test_v2_pinned_annotation_provenance_records_channel_mapping_source(self):
        mirror = self.fixture_v2["annotation_provenance"]["inspection_mirror"]
        self.assertEqual(mirror["repository"], "ColingPaper2018/DialogueAct-Tagger")
        self.assertEqual(
            mirror["commit"],
            "4307e9899ed9058e80d0861530de124d4f134317",
        )
        self.assertEqual(
            mirror["meeting_mapping"],
            "data/AMI/corpus/corpusResources/meetings.xml",
        )

    def test_v2_closeout_policy_is_stricter_than_original_minimum(self):
        policy = self.fixture_v2["close_out_policy"]
        self.assertEqual(policy["minimum_evaluated_long_cases"], 8)
        self.assertGreaterEqual(policy["minimum_aligned_human_positives"], 3)
        self.assertGreaterEqual(policy["minimum_foundation_human_positives"], 2)
        self.assertGreaterEqual(policy["minimum_foundation_sources"], 2)


if __name__ == "__main__":
    unittest.main()
