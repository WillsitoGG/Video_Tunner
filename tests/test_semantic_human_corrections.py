import json
import unittest
from pathlib import Path

from video_tunner.semantic_validation import evaluate_semantic_cases, validation_gate


FIXTURES = Path(__file__).parent / "fixtures"
BASE_FIXTURE = FIXTURES / "semantic_corpus_v1.json"
HUMAN_CORRECTIONS_FIXTURE = FIXTURES / "semantic_human_corrections_v1.json"


def combined_corpus() -> list[dict]:
    base = json.loads(BASE_FIXTURE.read_text(encoding="utf-8"))
    extra = json.loads(HUMAN_CORRECTIONS_FIXTURE.read_text(encoding="utf-8"))
    return base + extra


class SemanticHumanCorrectionBaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate_semantic_cases(combined_corpus(), mode="conservative")

    def test_human_correction_extension_is_traceable_and_bilingual(self):
        summary = self.report["summary"]
        self.assertEqual(summary["cases"], 26)
        self.assertEqual(summary["expected_events"], 14)
        self.assertEqual(
            summary["source_types"],
            {
                "constructed_negative": 6,
                "constructed_positive": 11,
                "human_speech_negative": 2,
                "human_speech_positive": 3,
                "human_speech_reference": 4,
            },
        )
        extra_ids = {
            "human-ami-es2012d-i-mean-correction",
            "human-ami-es2012d-i-mean-discourse",
            "human-corma-atfar-perdon-correction",
            "human-corma-ms-fa2-perdon-apology",
        }
        extra = [item for item in self.report["cases"] if item["id"] in extra_ids]
        self.assertEqual(len(extra), 4)
        self.assertTrue(all(item["source_reference"] for item in extra))

    def test_real_human_corrections_are_detected_review_only(self):
        for case_id, marker in (
            ("human-ami-es2012d-i-mean-correction", "I mean"),
            ("human-corma-atfar-perdon-correction", "Perdón"),
        ):
            with self.subTest(case_id=case_id):
                case = next(item for item in self.report["cases"] if item["id"] == case_id)
                self.assertEqual(case["false_negatives"], [])
                matched = [item for item in case["actual_candidates"] if item["removed_text"] == marker]
                self.assertEqual(len(matched), 1)
                self.assertEqual(matched[0]["kind"], "explicit_correction")
                self.assertEqual(matched[0]["decision"], "REVIEW")
                self.assertEqual(matched[0]["guard_status"], "review")

    def test_baseline_exposes_two_review_only_marker_false_positives(self):
        summary = self.report["summary"]
        self.assertEqual(summary["false_negative"], 0)
        self.assertEqual(summary["false_positive"], 2)
        self.assertEqual(summary["actual_candidates"], 16)
        self.assertEqual(summary["candidate_precision"], 0.875)
        self.assertEqual(summary["candidate_recall"], 1.0)
        self.assertEqual(summary["candidate_f1"], 0.9333)

        false_positive_ids = {
            item["id"]
            for item in self.report["cases"]
            if item["false_positives"]
        }
        self.assertEqual(
            false_positive_ids,
            {
                "human-ami-es2012d-i-mean-discourse",
                "human-corma-ms-fa2-perdon-apology",
            },
        )

    def test_baseline_fails_quality_gate_only_on_precision_not_safety(self):
        gate = validation_gate(
            self.report,
            minimum_precision=0.95,
            minimum_recall=0.95,
        )
        self.assertFalse(gate["passed"])
        self.assertEqual(gate["failures"], ["candidate_precision"])
        self.assertTrue(gate["checks"]["candidate_recall"])
        self.assertTrue(gate["checks"]["proposal_safety"])
        self.assertTrue(gate["checks"]["non_executable"])
        self.assertTrue(gate["checks"]["no_auto_apply"])

        summary = self.report["summary"]
        self.assertEqual(summary["unsafe_proposals"], 0)
        self.assertEqual(summary["decision_mismatches"], 0)
        self.assertEqual(summary["executable_decisions"], 0)
        self.assertEqual(summary["auto_apply_decisions"], 0)


if __name__ == "__main__":
    unittest.main()
