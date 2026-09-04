import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / ".github" / "scripts" / "discover_ami_repeat_cases.py"
SPEC = importlib.util.spec_from_file_location("discover_ami_repeat_cases", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AmiRepeatDiscoveryTests(unittest.TestCase):
    def _build_corpus(self, root: Path) -> Path:
        corpus = root / "data" / "AMI" / "corpus"
        (corpus / "disfluency").mkdir(parents=True)
        (corpus / "words").mkdir(parents=True)
        (corpus / "corpusResources").mkdir(parents=True)
        ns = "http://nite.sourceforge.net/"
        (corpus / "corpusResources" / "meetings.xml").write_text(
            f'''<?xml version="1.0"?>
<nite:root xmlns:nite="{ns}">
  <meeting observation="M1">
    <speaker nxt_agent="B" channel="1" />
  </meeting>
</nite:root>
''',
            encoding="utf-8",
        )
        words = [
            ("M1.B.words1", 1.0, 1.2, "before"),
            ("M1.B.words2", 2.0, 2.2, "we"),
            ("M1.B.words3", 2.2, 2.5, "really"),
            ("M1.B.words4", 2.5, 2.8, "can"),
            ("M1.B.words5", 2.9, 3.1, "we"),
            ("M1.B.words6", 3.1, 3.4, "really"),
            ("M1.B.words7", 3.4, 3.7, "can"),
            ("M1.B.words8", 3.8, 4.0, "after"),
        ]
        word_xml = [f'<nite:root xmlns:nite="{ns}">']
        for word_id, start, end, text in words:
            word_xml.append(
                f'  <w nite:id="{word_id}" starttime="{start}" endtime="{end}">{text}</w>'
            )
        word_xml.append("</nite:root>")
        (corpus / "words" / "M1.B.words.xml").write_text("\n".join(word_xml), encoding="utf-8")
        (corpus / "disfluency" / "M1.B.disfluency.xml").write_text(
            f'''<?xml version="1.0"?>
<nite:root xmlns:nite="{ns}" nite:id="M1.B.disfluency">
  <dsfl nite:id="M1.B.disfluency.alex.1">
    <nite:pointer role="dsfl-type" href="dsfl-types.xml#id(ami_dsfl_12)" />
    <dsfl nite:id="M1.B.disfluency.alex.2">
      <nite:pointer role="dsfl-type" href="dsfl-types.xml#id(ami_dsfl_19)" />
      <nite:child href="M1.B.words.xml#id(M1.B.words2)..id(M1.B.words4)" />
    </dsfl>
    <dsfl nite:id="M1.B.disfluency.alex.3">
      <nite:pointer role="dsfl-type" href="dsfl-types.xml#id(ami_dsfl_18)" />
      <nite:child href="M1.B.words.xml#id(M1.B.words5)..id(M1.B.words7)" />
    </dsfl>
  </dsfl>
</nite:root>
''',
            encoding="utf-8",
        )
        return corpus

    def test_normalisation_matches_production_contraction_token_count(self):
        self.assertEqual(MODULE._normalise("Let's all"), "lets all")
        self.assertEqual(MODULE._normalise("you can't"), "you cant")
        self.assertEqual(len(MODULE._normalise("what I've").split()), 2)

    def test_discovers_exact_three_token_repeat_with_channel_and_timings(self):
        with tempfile.TemporaryDirectory() as temp:
            corpus = self._build_corpus(Path(temp))
            cases = MODULE.discover_cases(corpus, min_tokens=3)
        self.assertEqual(len(cases), 1)
        case = cases[0]
        self.assertEqual(case["meeting"], "M1")
        self.assertEqual(case["speaker"], "B")
        self.assertEqual(case["channel"], 1)
        self.assertEqual(case["reparandum_text"], "we really can")
        self.assertEqual(case["reparans_text"], "we really can")
        self.assertEqual(case["token_count"], 3)
        self.assertEqual(case["reparandum_start"], 2.0)
        self.assertEqual(case["reparans_end"], 3.7)
        self.assertEqual(case["detector_expectation"], "long_detector_compatible")

    def test_minimum_token_filter_is_conservative(self):
        with tempfile.TemporaryDirectory() as temp:
            corpus = self._build_corpus(Path(temp))
            cases = MODULE.discover_cases(corpus, min_tokens=4)
        self.assertEqual(cases, [])

    def test_selection_limits_sources_and_cases_without_changing_labels(self):
        cases = []
        for source_index in range(3):
            for case_index in range(3):
                cases.append(
                    {
                        "id": f"c-{source_index}-{case_index}",
                        "meeting": f"M{source_index}",
                        "speaker": "A",
                        "channel": source_index,
                        "audio_source_id": f"M{source_index}-A",
                        "human_label": "removable_reparandum",
                        "token_count": 5 - case_index,
                        "clip_duration": 10.0 + case_index,
                    }
                )
        selected = MODULE.select_cases(cases, max_cases=4, max_sources=2, max_per_source=2)
        self.assertEqual(len(selected), 4)
        self.assertEqual(len({case["audio_source_id"] for case in selected}), 2)
        self.assertTrue(all(case["human_label"] == "removable_reparandum" for case in selected))

    def test_payload_uses_individual_headset_urls(self):
        selected = [
            {
                "id": "c1",
                "meeting": "M1",
                "speaker": "B",
                "channel": 2,
                "audio_source_id": "M1-B",
                "human_label": "removable_reparandum",
                "token_count": 3,
                "clip_duration": 8.0,
            }
        ]
        payload = MODULE.build_selection_payload(selected, selected)
        source = payload["audio_sources"]["M1-B"]
        self.assertEqual(source["audio"], "M1.Headset-2.wav")
        self.assertEqual(source["source_kind"], "individual_headset")
        self.assertTrue(source["url"].endswith("/M1/audio/M1.Headset-2.wav"))


if __name__ == "__main__":
    unittest.main()
