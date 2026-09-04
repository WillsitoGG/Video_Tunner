from __future__ import annotations

import unittest
from pathlib import Path

from video_tunner.eligibility import build_eligibility_assessments
from video_tunner.eligibility_validation import eligibility_gate, evaluate_eligibility_fixture
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming


FIXTURE = Path(__file__).parent / "fixtures" / "eligibility_v1.json"


def _tiny_transcript() -> TranscriptResult:
    words = (
        WordTiming("i", 0.1, 0.2, 0.99),
        WordTiming("mean", 0.2, 0.3, 0.99),
        WordTiming("how", 0.3, 0.5, 0.99),
    )
    return TranscriptResult(
        language="en",
        language_probability=0.99,
        model="fixture",
        device="cpu",
        compute_type="int8",
        segments=(TranscriptSegment("i mean how", 0.1, 0.5, words),),
    )


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

    def test_ambiguous_correction_without_target_is_diagnosed_as_scope_blocker(self):
        candidate = {
            "id": "explicit_correction-0001",
            "kind": "explicit_correction",
            "start": 0.1,
            "end": 0.3,
        }
        join = {
            "id": "join-assessment-0001",
            "candidate_id": candidate["id"],
            "candidate_kind": candidate["kind"],
            "status": "invalid_or_unbounded_target",
            "target_span": None,
        }
        scope = {"candidate_id": candidate["id"], "status": "ambiguous"}
        semantic = {
            "id": "semantic-0001",
            "candidate_id": candidate["id"],
            "candidate_kind": candidate["kind"],
            "decision": "REVIEW",
            "guard_status": "review",
            "executable": False,
            "auto_apply": False,
        }
        acoustic = {
            "id": "acoustic-0001",
            "join_assessment_id": join["id"],
            "candidate_id": candidate["id"],
            "status": "blocked_by_context",
            "measurement_available": False,
        }
        result = build_eligibility_assessments(
            _tiny_transcript(),
            [candidate],
            semantic_decisions=[semantic],
            correction_scopes=[scope],
            filler_assessments=[],
            join_assessments=[join],
            acoustic_join_assessments=[acoustic],
        )[0]
        self.assertEqual(result["status"], "blocked_correction_scope")
        self.assertEqual(result["removed_text_validation"]["reason"], "missing_target_span")
        self.assertFalse(result["future_promotion_candidate"])
        self.assertFalse(result["safe_for_cut"])
        self.assertFalse(result["executable"])
        self.assertFalse(result["auto_apply"])


if __name__ == "__main__":
    unittest.main()
