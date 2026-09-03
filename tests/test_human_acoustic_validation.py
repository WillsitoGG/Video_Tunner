import json
import unittest
from pathlib import Path

from video_tunner.human_acoustic_validation import build_human_join_evidence

FIXTURE = Path(__file__).parent / "fixtures" / "human_acoustic_ami_v1.json"


class HumanAcousticFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.evidence = build_human_join_evidence(cls.fixture)

    def test_fixture_is_traceable_to_real_ami_audio_and_large_v3_turbo_run(self):
        self.assertEqual(self.fixture["source"]["corpus"], "AMI Meeting Corpus")
        self.assertEqual(self.fixture["source"]["meeting"], "ES2012d")
        self.assertEqual(self.fixture["source"]["license"], "CC BY 4.0")
        self.assertEqual(
            self.fixture["source"]["sha256"],
            "39FCDE566E2D1BC7EC40A31DEC19251CC253AAC54BE94713E68EEA3008AF4F8D",
        )
        self.assertEqual(self.fixture["asr_reference"]["workflow_run"], 33755013415)
        self.assertEqual(self.fixture["asr_reference"]["model"], "large-v3-turbo")

    def test_frozen_real_asr_cases_preserve_expected_join_context_contract(self):
        records = self.evidence["records"]
        self.assertEqual(len(records), 3)
        by_id = {record["case"]["id"]: record for record in records}

        control = by_id["ami-human-pause-control-0311"]
        self.assertEqual(control["join"]["status"], "join_context_only")

        retake = by_id["ami-human-retake-protected-0311"]
        self.assertEqual(retake["join"]["status"], "repair_or_protected_context_risk")

        correction = by_id["ami-human-correction-ambiguous-0250"]
        self.assertEqual(correction["correction_scopes"][0]["status"], "ambiguous")
        self.assertEqual(correction["join"]["status"], "invalid_or_unbounded_target")

    def test_all_frozen_human_join_evidence_remains_non_executable(self):
        for record in self.evidence["records"]:
            join = record["join"]
            self.assertFalse(join["safe_for_cut"])
            self.assertFalse(join["executable"])
            self.assertFalse(join["auto_apply"])


if __name__ == "__main__":
    unittest.main()
