import json
import unittest
from pathlib import Path

from video_tunner.semantic_validation import evaluate_semantic_cases, validation_gate


FIXTURE = Path(__file__).parent / "fixtures" / "semantic_corpus_v1.json"


def corpus() -> list[dict]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class SemanticValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = evaluate_semantic_cases(corpus(), mode="conservative")

    def test_corpus_is_large_enough_to_exercise_risk_classes(self):
        summary = self.report["summary"]
        self.assertEqual(summary["cases"], 16)
        self.assertEqual(summary["expected_events"], 11)
        self.assertGreaterEqual(summary["actual_candidates"], 11)

    def test_baseline_candidate_metrics_are_measured_not_hidden(self):
        summary = self.report["summary"]
        self.assertEqual(summary["false_negative"], 0)
        self.assertEqual(summary["false_positive"], 2)
        self.assertEqual(summary["candidate_recall"], 1.0)
        self.assertEqual(summary["candidate_precision"], 0.8462)
        self.assertEqual(summary["candidate_f1"], 0.9167)

        false_positive_cases = {
            item["id"]
            for item in self.report["cases"]
            if item["false_positives"]
        }
        self.assertEqual(
            false_positive_cases,
            {"legitimate-reuse", "literal-quiero-decir"},
        )

    def test_false_positive_candidates_remain_review_only(self):
        for case in self.report["cases"]:
            if case["id"] not in {"legitimate-reuse", "literal-quiero-decir"}:
                continue
            self.assertTrue(case["actual_candidates"])
            self.assertTrue(
                all(item["decision"] == "REVIEW" for item in case["actual_candidates"]),
                case["id"],
            )

    def test_decision_contract_has_zero_safety_violations(self):
        summary = self.report["summary"]
        self.assertEqual(summary["decision_mismatches"], 0)
        self.assertEqual(summary["unsafe_proposals"], 0)
        self.assertEqual(summary["missing_safe_proposals"], 0)
        self.assertEqual(summary["executable_decisions"], 0)
        self.assertEqual(summary["auto_apply_decisions"], 0)

    def test_phase2c_foundation_gate_passes_without_enabling_edits(self):
        gate = validation_gate(
            self.report,
            minimum_precision=0.80,
            minimum_recall=0.90,
        )
        self.assertTrue(gate["passed"], gate)
        self.assertTrue(gate["checks"]["proposal_safety"])
        self.assertTrue(gate["checks"]["non_executable"])
        self.assertTrue(gate["checks"]["no_auto_apply"])


if __name__ == "__main__":
    unittest.main()
