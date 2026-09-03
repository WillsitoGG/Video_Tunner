from __future__ import annotations

import unittest
from pathlib import Path

from video_tunner.human_acoustic_validation import build_human_join_evidence
from video_tunner.human_eligibility_validation import (
    _frozen_semantic_decisions,
    load_human_eligibility_inputs,
)


FIXTURES = Path(__file__).parent / "fixtures"
EXPECTATIONS = FIXTURES / "human_eligibility_ami_v1.json"
HUMAN = FIXTURES / "human_acoustic_ami_v1.json"


class HumanEligibilityFixtureTests(unittest.TestCase):
    def test_expectations_cover_exactly_the_frozen_human_cases(self):
        expectations, human = load_human_eligibility_inputs(EXPECTATIONS, HUMAN)
        expected_ids = {str(item["id"]) for item in expectations["cases"]}
        human_ids = {str(item["id"]) for item in human["cases"]}
        self.assertEqual(expected_ids, human_ids)
        self.assertEqual(expectations["semantic_reference"]["workflow_run"], 33755013415)
        self.assertEqual(human["asr_reference"]["workflow_run"], 33755013415)

    def test_frozen_semantic_decisions_remain_non_executable(self):
        expectations, human = load_human_eligibility_inputs(EXPECTATIONS, HUMAN)
        context = build_human_join_evidence(human)
        records = {str(item["case"]["id"]): item for item in context["records"]}
        decisions = _frozen_semantic_decisions(expectations, records)
        self.assertEqual(len(decisions), 2)
        self.assertEqual({item["decision"] for item in decisions}, {"REVIEW"})
        for item in decisions:
            self.assertFalse(item["executable"])
            self.assertFalse(item["auto_apply"])
            self.assertIn(item["candidate_id"], {r["candidate"]["id"] for r in records.values()})

    def test_human_contract_has_one_control_pass_and_two_expected_blockers(self):
        expectations, _ = load_human_eligibility_inputs(EXPECTATIONS, HUMAN)
        statuses = [str(item["expected_eligibility_status"]) for item in expectations["cases"]]
        self.assertEqual(statuses.count("foundation_guards_pass"), 1)
        self.assertIn("blocked_semantic_decision", statuses)
        self.assertIn("blocked_correction_scope", statuses)
        promotion = [item for item in expectations["cases"] if item["expected_future_promotion_candidate"]]
        self.assertEqual(len(promotion), 1)
        self.assertEqual(promotion[0]["id"], "ami-human-pause-control-0311")


if __name__ == "__main__":
    unittest.main()
