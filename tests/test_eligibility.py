from __future__ import annotations

import unittest
from pathlib import Path

from video_tunner.eligibility_validation import eligibility_gate, evaluate_eligibility_fixture


FIXTURE = Path(__file__).parent / "fixtures" / "eligibility_v1.json"


class EligibilityValidationTests(unittest.TestCase):
    def test_combined_policy_status_contract_is_exact(self):
        metrics = evaluate_eligibility_fixture(FIXTURE)
        self.assertEqual(metrics["status_mismatch_count"], 0, metrics["status_mismatches"])
        self.assertEqual(metrics["removed_text_failure_count"], 0, metrics["removed_text_failures"])

    def test_fixture_exercises_all_required_guard_classes(self):
        metrics = evaluate_eligibility_fixture(FIXTURE)
        self.assertGreaterEqual(metrics["cases"], 10)
        self.assertEqual(metrics["missing_required_statuses"], [])
        self.assertGreaterEqual(metrics["future_promotion_candidates"], 3)

    def test_combined_policy_never_authorizes_or_executes_a_cut(self):
        metrics = evaluate_eligibility_fixture(FIXTURE)
        self.assertEqual(metrics["safety_violation_count"], 0, metrics["safety_violations"])
        self.assertEqual(metrics["safe_for_cut"], 0)
        self.assertEqual(metrics["executable"], 0)
        self.assertEqual(metrics["auto_apply"], 0)

    def test_phase2d4_gate_passes(self):
        metrics = evaluate_eligibility_fixture(FIXTURE)
        gate = eligibility_gate(metrics)
        self.assertTrue(gate["passed"], gate)


if __name__ == "__main__":
    unittest.main()
