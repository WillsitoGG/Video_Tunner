import json
import unittest
from pathlib import Path

from video_tunner.join_safety_validation import (
    evaluate_join_safety_cases,
    join_safety_gate,
)

FIXTURE = Path(__file__).parent / "fixtures" / "join_safety_v1.json"


class JoinSafetyValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.report = evaluate_join_safety_cases(cls.cases)

    def test_corpus_exercises_context_and_risk_classes(self):
        counts = self.report["metrics"]["expected_status_counts"]
        self.assertGreaterEqual(len(self.cases), 15)
        self.assertGreaterEqual(counts.get("join_context_only", 0), 3)
        self.assertGreaterEqual(counts.get("repair_or_protected_context_risk", 0), 4)
        self.assertGreaterEqual(counts.get("critical_lexical_context_risk", 0), 2)
        self.assertGreaterEqual(counts.get("segment_boundary_risk", 0), 1)
        self.assertGreaterEqual(counts.get("sentence_boundary_risk", 0), 1)
        self.assertGreaterEqual(counts.get("invalid_or_unbounded_target", 0), 2)
        self.assertGreaterEqual(counts.get("transcript_edge", 0), 1)

    def test_join_status_and_target_contract_are_exact_on_v1_corpus(self):
        metrics = self.report["metrics"]
        self.assertEqual(metrics["status_mismatches"], 0)
        self.assertEqual(metrics["target_source_mismatches"], 0)
        self.assertEqual(metrics["bilateral_mismatches"], 0)
        self.assertEqual(metrics["expected_status_counts"], metrics["actual_status_counts"])
        self.assertEqual(metrics["status_accuracy"], 1.0)

    def test_human_ami_retake_is_never_treated_as_ordinary_join(self):
        case = next(
            item for item in self.report["cases"] if item["id"] == "human-ami-retake-join-risk"
        )
        self.assertEqual(case["actual_status"], "repair_or_protected_context_risk")
        self.assertEqual(case["actual_target_source"], "candidate_word_span")
        self.assertTrue(case["actual_bilateral"])
        self.assertFalse(case["safe_for_cut"])
        self.assertFalse(case["executable"])
        self.assertFalse(case["auto_apply"])

    def test_invalid_or_ambiguous_targets_fail_safe(self):
        for case_id in ("ambiguous-correction-no-target", "corrupted-semantic-span"):
            case = next(item for item in self.report["cases"] if item["id"] == case_id)
            self.assertEqual(case["actual_status"], "invalid_or_unbounded_target")
            self.assertIsNone(case["actual_target_source"])
            self.assertFalse(case["actual_bilateral"])

    def test_join_gate_passes_without_authorizing_cuts(self):
        gate = join_safety_gate(self.report)
        self.assertTrue(gate["passed"], gate)
        self.assertTrue(all(gate["checks"].values()))
        self.assertEqual(self.report["metrics"]["safety_violations"], 0)


if __name__ == "__main__":
    unittest.main()
