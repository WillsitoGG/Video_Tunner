import json
import unittest
from pathlib import Path

from video_tunner.filler_context_validation import (
    evaluate_filler_context_cases,
    filler_context_gate,
)

FIXTURE = Path(__file__).parent / "fixtures" / "filler_context_v1.json"


class FillerContextValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.report = evaluate_filler_context_cases(cls.cases)

    def test_corpus_exercises_required_context_classes(self):
        counts = self.report["metrics"]["expected_status_counts"]
        self.assertGreaterEqual(len(self.cases), 15)
        self.assertGreaterEqual(counts.get("isolated_hesitation", 0), 2)
        self.assertGreaterEqual(counts.get("hesitation_cluster", 0), 4)
        self.assertGreaterEqual(counts.get("protected_repair_context", 0), 3)
        self.assertGreaterEqual(counts.get("boundary_hesitation", 0), 5)
        self.assertGreaterEqual(counts.get("uncertain_asr", 0), 1)

    def test_context_statuses_are_exact_on_v1_corpus(self):
        metrics = self.report["metrics"]
        self.assertEqual(metrics["record_count_mismatches"], 0)
        self.assertEqual(metrics["status_mismatches"], 0)
        self.assertEqual(metrics["expected_status_counts"], metrics["actual_status_counts"])
        self.assertEqual(metrics["status_accuracy"], 1.0)

    def test_repair_fillers_are_protected_and_linked(self):
        metrics = self.report["metrics"]
        self.assertGreaterEqual(metrics["expected_protected_repair"], 3)
        self.assertEqual(
            metrics["protected_repair_correct"], metrics["expected_protected_repair"]
        )
        self.assertEqual(metrics["repair_link_mismatches"], 0)
        self.assertEqual(metrics["repair_protection_recall"], 1.0)

    def test_human_ami_retake_filler_is_protected(self):
        case = next(item for item in self.report["cases"] if item["id"] == "human-ami-retake-filler")
        self.assertEqual(case["actual_statuses"], ["protected_repair_context"])
        self.assertTrue(case["actual_repair_link"])
        self.assertFalse(case["safe_for_cut"])
        self.assertFalse(case["executable"])
        self.assertFalse(case["auto_apply"])

    def test_filler_context_gate_passes_without_enabling_edits(self):
        gate = filler_context_gate(self.report)
        self.assertTrue(gate["passed"], gate)
        self.assertTrue(all(gate["checks"].values()))
        self.assertEqual(self.report["metrics"]["safety_violations"], 0)


if __name__ == "__main__":
    unittest.main()
