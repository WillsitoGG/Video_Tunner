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
        self.assertEqual(summary["cases"], 17)
        self.assertEqual(summary["expected_events"], 11)
        self.assertEqual(summary["actual_candidates"], 11)

    def test_tuned_candidate_metrics_reach_clean_labelled_baseline(self):
        summary = self.report["summary"]
        self.assertEqual(summary["false_negative"], 0)
        self.assertEqual(summary["false_positive"], 0)
        self.assertEqual(summary["candidate_recall"], 1.0)
        self.assertEqual(summary["candidate_precision"], 1.0)
        self.assertEqual(summary["candidate_f1"], 1.0)
        self.assertFalse(any(item["false_positives"] for item in self.report["cases"]))

    def test_known_baseline_false_positives_are_now_rejected_conservatively(self):
        controlled = {
            item["id"]: item
            for item in self.report["cases"]
            if item["id"] in {
                "legitimate-reuse",
                "literal-quiero-decir",
                "literal-lo-que-quiero-decir",
            }
        }
        self.assertEqual(len(controlled), 3)
        self.assertTrue(all(not item["actual_candidates"] for item in controlled.values()))

    def test_decision_contract_has_zero_safety_violations(self):
        summary = self.report["summary"]
        self.assertEqual(summary["decision_mismatches"], 0)
        self.assertEqual(summary["unsafe_proposals"], 0)
        self.assertEqual(summary["missing_safe_proposals"], 0)
        self.assertEqual(summary["executable_decisions"], 0)
        self.assertEqual(summary["auto_apply_decisions"], 0)

    def test_phase2c_gate_passes_without_enabling_edits(self):
        gate = validation_gate(
            self.report,
            minimum_precision=0.95,
            minimum_recall=0.95,
        )
        self.assertTrue(gate["passed"], gate)
        self.assertTrue(gate["checks"]["proposal_safety"])
        self.assertTrue(gate["checks"]["non_executable"])
        self.assertTrue(gate["checks"]["no_auto_apply"])


if __name__ == "__main__":
    unittest.main()
