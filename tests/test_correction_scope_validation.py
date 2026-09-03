import json
import unittest
from pathlib import Path

from video_tunner.correction_scope_validation import (
    correction_scope_gate,
    evaluate_correction_scope_cases,
)


FIXTURE = Path(__file__).parent / "fixtures" / "correction_scope_v1.json"


def load_cases() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))["cases"]


class CorrectionScopeValidationTests(unittest.TestCase):
    def test_scope_corpus_exercises_bounded_ambiguous_and_no_candidate_cases(self):
        cases = load_cases()
        self.assertGreaterEqual(len(cases), 12)
        statuses = {case.get("expected_status") for case in cases}
        self.assertIn("bounded", statuses)
        self.assertIn("ambiguous", statuses)
        self.assertIn(None, statuses)
        self.assertTrue(any(case.get("source_type") == "human_transcript_reference" for case in cases))

    def test_scope_metrics_are_exact_on_v1_corpus(self):
        report = evaluate_correction_scope_cases(load_cases())
        metrics = report["metrics"]
        self.assertEqual(metrics["candidate_misses"], 0)
        self.assertEqual(metrics["candidate_false_positives"], 0)
        self.assertEqual(metrics["scope_count_mismatches"], 0)
        self.assertEqual(metrics["bounded_wrong"], 0)
        self.assertEqual(metrics["status_mismatches"], 0)
        self.assertEqual(metrics["strategy_mismatches"], 0)
        self.assertEqual(metrics["attempt_text_mismatches"], 0)
        self.assertEqual(metrics["unsafe_bounded"], 0)
        self.assertEqual(metrics["safety_violations"], 0)
        self.assertEqual(metrics["bounded_exactness"], 1.0)
        self.assertEqual(metrics["scope_status_accuracy"], 1.0)

    def test_scope_gate_passes_without_creating_executable_edits(self):
        report = evaluate_correction_scope_cases(load_cases())
        gate = correction_scope_gate(report)
        self.assertTrue(gate["passed"], gate)
        self.assertTrue(all(gate["checks"].values()))
        self.assertTrue(all(case["safe_for_cut"] is False for case in report["cases"] if case["scope_count"] == 1))
        self.assertTrue(all(case["executable"] is False for case in report["cases"] if case["scope_count"] == 1))
        self.assertTrue(all(case["auto_apply"] is False for case in report["cases"] if case["scope_count"] == 1))

    def test_ami_question_reframe_remains_detected_but_scope_ambiguous(self):
        report = evaluate_correction_scope_cases(load_cases())
        case = next(item for item in report["cases"] if item["id"] == "scope-ami-question-reframe-en")
        self.assertTrue(case["expect_candidate"])
        self.assertEqual(case["scope_count"], 1)
        self.assertEqual(case["actual_status"], "ambiguous")
        self.assertIsNone(case["actual_attempt_text"])


if __name__ == "__main__":
    unittest.main()
