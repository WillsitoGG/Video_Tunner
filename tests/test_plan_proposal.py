import copy
import unittest

from video_tunner.approval import build_approval_record
from video_tunner.plan_proposal import (
    GLOBAL_LIMITS,
    build_approved_edit_plan_proposal,
)


ANALYSIS_SHA = "a" * 64


def build_analysis(intervals, *, duration=100.0, mode="conservative"):
    candidates = []
    eligibilities = []
    promotions = []
    for index, (start, end) in enumerate(intervals, start=1):
        candidate_id = f"possible_repetition-{index:04d}"
        eligibility_id = f"eligibility-assessment-{index:04d}"
        promotion_id = f"promotion-assessment-{index:04d}"
        target = {
            "source": "candidate_word_span",
            "text": f"repeat {index}",
            "start": float(start),
            "end": float(end),
            "word_start_index": index * 3,
            "word_end_index_exclusive": index * 3 + 2,
        }
        candidates.append(
            {
                "id": candidate_id,
                "kind": "possible_repetition",
                "start": float(start),
                "end": float(end),
            }
        )
        eligibilities.append(
            {
                "id": eligibility_id,
                "candidate_id": candidate_id,
                "candidate_kind": "possible_repetition",
                "status": "foundation_guards_pass",
                "future_promotion_candidate": True,
                "removed_text_validation": {"valid": True, **target},
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        )
        promotions.append(
            {
                "id": promotion_id,
                "eligibility_assessment_id": eligibility_id,
                "candidate_id": candidate_id,
                "candidate_kind": "possible_repetition",
                "mode": mode,
                "status": "eligible_for_promotion_review",
                "blockers": [],
                "promotion_review_candidate": True,
                "requires_explicit_approval": True,
                "approval_state": "required",
                "approved": False,
                "target_preview": target,
                "edit": None,
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        )
    return {
        "schema_version": 9,
        "source": {
            "file": "video.mp4",
            "duration_seconds": float(duration),
            "sha256": "b" * 64,
        },
        "mode": mode,
        "candidates": candidates,
        "eligibility_assessments": eligibilities,
        "promotion_assessments": promotions,
    }


def approve_all(analysis):
    records = []
    for promotion in analysis["promotion_assessments"]:
        records.append(
            build_approval_record(
                analysis,
                promotion["id"],
                decision="APPROVE",
                actor="reviewer",
                reason="Exact repetition reviewed.",
                analysis_sha256=ANALYSIS_SHA,
                created_utc="2026-09-04T17:30:00+00:00",
            )
        )
    return records


class ApprovedEditPlanProposalTests(unittest.TestCase):
    def test_limits_are_precommitted_and_mode_independent(self):
        self.assertEqual(GLOBAL_LIMITS["max_semantic_edits"], 10)
        self.assertEqual(GLOBAL_LIMITS["max_removed_seconds"], 30.0)
        self.assertEqual(GLOBAL_LIMITS["max_removed_fraction"], 0.05)

    def test_valid_approved_records_create_review_only_proposal(self):
        analysis = build_analysis([(10.0, 11.0), (20.0, 21.5)], duration=100.0)
        proposal = build_approved_edit_plan_proposal(
            analysis,
            approve_all(analysis),
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(proposal["status"], "proposal_ready_for_global_review")
        self.assertEqual(len(proposal["proposed_edits"]), 2)
        self.assertNotIn("edits", proposal)
        self.assertEqual(proposal["summary"]["removed_seconds"], 2.5)
        self.assertEqual(proposal["summary"]["removed_fraction"], 0.025)
        self.assertTrue(proposal["requires_global_review"])
        self.assertFalse(proposal["globally_approved"])
        self.assertFalse(proposal["render_authorization"])
        self.assertFalse(proposal["executable"])
        self.assertFalse(proposal["auto_apply"])
        for edit in proposal["proposed_edits"]:
            self.assertEqual(edit["action"], "remove")
            self.assertFalse(edit["globally_approved"])
            self.assertFalse(edit["render_authorized"])
            self.assertFalse(edit["executable"])
            self.assertFalse(edit["auto_apply"])

    def test_rejected_approval_vetoes_entire_proposal(self):
        analysis = build_analysis([(10.0, 11.0), (20.0, 21.0)])
        approvals = approve_all(analysis)
        approvals[1] = build_approval_record(
            analysis,
            "promotion-assessment-0002",
            decision="REJECT",
            actor="reviewer",
            reason="Intentional repetition.",
            analysis_sha256=ANALYSIS_SHA,
        )
        proposal = build_approved_edit_plan_proposal(
            analysis, approvals, analysis_sha256=ANALYSIS_SHA
        )
        self.assertEqual(proposal["status"], "blocked_invalid_or_conflicting_approval")
        self.assertEqual(proposal["proposed_edits"], [])
        self.assertEqual(proposal["blockers"][0]["validation_status"], "valid_rejected")

    def test_stale_approval_vetoes_entire_proposal(self):
        analysis = build_analysis([(10.0, 11.0)])
        approval = approve_all(analysis)[0]
        proposal = build_approved_edit_plan_proposal(
            analysis, [approval], analysis_sha256="c" * 64
        )
        self.assertEqual(proposal["status"], "blocked_invalid_or_conflicting_approval")
        self.assertEqual(proposal["blockers"][0]["validation_status"], "stale_analysis")
        self.assertEqual(proposal["proposed_edits"], [])

    def test_duplicate_approval_vetoes_entire_proposal(self):
        analysis = build_analysis([(10.0, 11.0)])
        approval = approve_all(analysis)[0]
        proposal = build_approved_edit_plan_proposal(
            analysis,
            [approval, copy.deepcopy(approval)],
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(proposal["status"], "blocked_invalid_or_conflicting_approval")
        self.assertTrue(any(item["reason"] == "duplicate_approved_target" for item in proposal["blockers"]))
        self.assertEqual(proposal["proposed_edits"], [])

    def test_overlapping_targets_veto_entire_proposal(self):
        analysis = build_analysis([(10.0, 12.0), (11.5, 13.0)], duration=100.0)
        proposal = build_approved_edit_plan_proposal(
            analysis,
            approve_all(analysis),
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(proposal["status"], "blocked_overlapping_approved_targets")
        self.assertEqual(proposal["proposed_edits"], [])
        self.assertEqual(proposal["blockers"][0]["reason"], "approved_targets_overlap")

    def test_target_outside_source_timeline_vetoes_entire_proposal(self):
        analysis = build_analysis([(99.0, 101.0)], duration=100.0)
        approval = approve_all(analysis)[0]
        proposal = build_approved_edit_plan_proposal(
            analysis, [approval], analysis_sha256=ANALYSIS_SHA
        )
        self.assertEqual(proposal["status"], "blocked_invalid_or_conflicting_approval")
        self.assertEqual(proposal["blockers"][0]["reason"], "approved_target_outside_source_timeline")

    def test_max_edit_count_is_enforced_independently(self):
        intervals = [(1.0 + i * 2.0, 1.1 + i * 2.0) for i in range(11)]
        analysis = build_analysis(intervals, duration=100.0)
        proposal = build_approved_edit_plan_proposal(
            analysis,
            approve_all(analysis),
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(proposal["status"], "blocked_global_limits")
        reasons = {item["reason"] for item in proposal["blockers"]}
        self.assertIn("max_semantic_edits_exceeded", reasons)
        self.assertNotIn("max_removed_seconds_exceeded", reasons)
        self.assertNotIn("max_removed_fraction_exceeded", reasons)

    def test_max_removed_seconds_is_enforced_independently(self):
        analysis = build_analysis([(10.0, 26.0), (40.0, 56.0)], duration=1000.0)
        proposal = build_approved_edit_plan_proposal(
            analysis,
            approve_all(analysis),
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(proposal["status"], "blocked_global_limits")
        reasons = {item["reason"] for item in proposal["blockers"]}
        self.assertIn("max_removed_seconds_exceeded", reasons)
        self.assertNotIn("max_semantic_edits_exceeded", reasons)
        self.assertNotIn("max_removed_fraction_exceeded", reasons)

    def test_max_removed_fraction_is_enforced_independently(self):
        analysis = build_analysis([(10.0, 13.0), (20.0, 23.0)], duration=100.0)
        proposal = build_approved_edit_plan_proposal(
            analysis,
            approve_all(analysis),
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(proposal["status"], "blocked_global_limits")
        reasons = {item["reason"] for item in proposal["blockers"]}
        self.assertIn("max_removed_fraction_exceeded", reasons)
        self.assertNotIn("max_semantic_edits_exceeded", reasons)
        self.assertNotIn("max_removed_seconds_exceeded", reasons)

    def test_no_approvals_is_blocked(self):
        analysis = build_analysis([(10.0, 11.0)])
        proposal = build_approved_edit_plan_proposal(
            analysis, [], analysis_sha256=ANALYSIS_SHA
        )
        self.assertEqual(proposal["status"], "blocked_no_approved_records")
        self.assertEqual(proposal["proposed_edits"], [])
        self.assertFalse(proposal["render_authorization"])


if __name__ == "__main__":
    unittest.main()
