import json
import unittest
from pathlib import Path

from video_tunner.acoustic_join_validation import (
    acoustic_join_gate,
    evaluate_acoustic_join_cases,
)

FIXTURE = Path(__file__).parent / "fixtures" / "acoustic_join_v1.json"


class AcousticJoinValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(FIXTURE.read_text(encoding="utf-8"))
        cls.report = evaluate_acoustic_join_cases(cls.cases)

    def test_corpus_exercises_context_and_discontinuity_classes(self):
        statuses = {case["expected_status"] for case in self.cases}
        self.assertGreaterEqual(len(self.cases), 10)
        self.assertIn("acoustic_context_only", statuses)
        self.assertIn("low_energy_boundary_context", statuses)
        self.assertIn("level_discontinuity_risk", statuses)
        self.assertIn("waveform_discontinuity_risk", statuses)
        self.assertIn("combined_discontinuity_risk", statuses)
        self.assertIn("insufficient_audio_context", statuses)
        self.assertIn("blocked_by_context", statuses)

    def test_statuses_are_exact_on_v1_corpus(self):
        metrics = self.report["metrics"]
        self.assertEqual(metrics["status_mismatches"], 0)
        self.assertEqual(metrics["status_accuracy"], 1.0)
        self.assertEqual(metrics["expected_status_counts"], metrics["actual_status_counts"])

    def test_measurement_contract_is_exact(self):
        self.assertEqual(self.report["metrics"]["measurement_mismatches"], 0)

    def test_risk_cases_are_detected(self):
        metrics = self.report["metrics"]
        self.assertGreater(metrics["expected_risk_cases"], 0)
        self.assertEqual(metrics["risk_recall"], 1.0)

    def test_acoustic_gate_passes_without_authorizing_cuts(self):
        gate = acoustic_join_gate(self.report)
        self.assertTrue(gate["passed"], gate)
        self.assertEqual(self.report["metrics"]["safety_violations"], 0)
        for case in self.report["cases"]:
            self.assertFalse(case["safe_for_cut"])
            self.assertFalse(case["executable"])
            self.assertFalse(case["auto_apply"])


if __name__ == "__main__":
    unittest.main()
