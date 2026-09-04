import copy
import unittest

from video_tunner.approval import build_approval_record
from video_tunner.execution_authorization import (
    build_execution_authorization,
    validate_execution_authorization,
)
from video_tunner.plan_proposal import build_approved_edit_plan_proposal


ANALYSIS_SHA = "a" * 64
PROPOSAL_SHA = "c" * 64


def build_analysis():
    target = {
        "source": "candidate_word_span",
        "text": "proyecto central listo",
        "start": 10.0,
        "end": 11.0,
        "word_start_index": 3,
        "word_end_index_exclusive": 6,
    }
    return {
        "schema_version": 9,
        "source": {
            "file": "video.mp4",
            "duration_seconds": 100.0,
            "sha256": "b" * 64,
        },
        "mode": "conservative",
        "candidates": [
            {
                "id": "possible_repetition-0001",
                "kind": "possible_repetition",
                "start": 10.0,
                "end": 11.0,
            }
        ],
        "eligibility_assessments": [
            {
                "id": "eligibility-assessment-0001",
                "candidate_id": "possible_repetition-0001",
                "candidate_kind": "possible_repetition",
                "status": "foundation_guards_pass",
                "future_promotion_candidate": True,
                "removed_text_validation": {"valid": True, **target},
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        ],
        "promotion_assessments": [
            {
                "id": "promotion-assessment-0001",
                "eligibility_assessment_id": "eligibility-assessment-0001",
                "candidate_id": "possible_repetition-0001",
                "candidate_kind": "possible_repetition",
                "mode": "conservative",
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
        ],
    }


def build_ready_proposal(analysis):
    approval = build_approval_record(
        analysis,
        "promotion-assessment-0001",
        decision="APPROVE",
        actor="reviewer",
        reason="Exact repetition reviewed.",
        analysis_sha256=ANALYSIS_SHA,
        created_utc="2026-09-04T18:00:00+00:00",
    )
    return build_approved_edit_plan_proposal(
        analysis,
        [approval],
        analysis_sha256=ANALYSIS_SHA,
    )


class ExecutionAuthorizationTests(unittest.TestCase):
    def test_approve_authorizes_materialization_and_gated_render_not_proposal_render(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        authorization = build_execution_authorization(
            analysis,
            proposal,
            decision="APPROVE",
            actor="global-reviewer",
            reason="Whole bounded proposal reviewed.",
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
            created_utc="2026-09-04T19:00:00+00:00",
        )
        self.assertTrue(authorization["authorized"])
        self.assertTrue(authorization["edit_plan_materialization_authorized"])
        self.assertTrue(authorization["semantic_render_authorization"])
        self.assertFalse(authorization["proposal_render_authorization"])
        self.assertFalse(authorization["executable"])
        self.assertFalse(authorization["auto_apply"])

        validation = validate_execution_authorization(
            analysis,
            proposal,
            authorization,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        self.assertEqual(validation["status"], "valid_authorized")
        self.assertTrue(validation["authorized"])
        self.assertTrue(validation["semantic_render_authorization"])

    def test_reject_is_valid_but_has_no_execution_capability(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        authorization = build_execution_authorization(
            analysis,
            proposal,
            decision="REJECT",
            actor="global-reviewer",
            reason="Proposal rejected after global review.",
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        validation = validate_execution_authorization(
            analysis,
            proposal,
            authorization,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        self.assertEqual(validation["status"], "valid_rejected")
        self.assertFalse(validation["authorized"])
        self.assertFalse(validation["edit_plan_materialization_authorized"])
        self.assertFalse(validation["semantic_render_authorization"])

    def test_changed_analysis_hash_marks_authorization_stale(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        authorization = build_execution_authorization(
            analysis,
            proposal,
            decision="APPROVE",
            actor="reviewer",
            reason="Reviewed.",
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        validation = validate_execution_authorization(
            analysis,
            proposal,
            authorization,
            analysis_sha256="d" * 64,
            proposal_sha256=PROPOSAL_SHA,
        )
        self.assertEqual(validation["status"], "stale_analysis")
        self.assertFalse(validation["authorized"])

    def test_changed_proposal_hash_marks_authorization_stale(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        authorization = build_execution_authorization(
            analysis,
            proposal,
            decision="APPROVE",
            actor="reviewer",
            reason="Reviewed.",
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        validation = validate_execution_authorization(
            analysis,
            proposal,
            authorization,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256="e" * 64,
        )
        self.assertEqual(validation["status"], "stale_proposal")
        self.assertFalse(validation["authorized"])

    def test_tampered_evidence_fingerprint_fails_safe(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        authorization = build_execution_authorization(
            analysis,
            proposal,
            decision="APPROVE",
            actor="reviewer",
            reason="Reviewed.",
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        authorization["proposal_evidence_fingerprint"] = "f" * 64
        validation = validate_execution_authorization(
            analysis,
            proposal,
            authorization,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        self.assertEqual(validation["status"], "stale_evidence")
        self.assertFalse(validation["authorized"])

    def test_tampered_capability_fields_are_invalid(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        authorization = build_execution_authorization(
            analysis,
            proposal,
            decision="APPROVE",
            actor="reviewer",
            reason="Reviewed.",
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        tampered = copy.deepcopy(authorization)
        tampered["proposal_render_authorization"] = True
        validation = validate_execution_authorization(
            analysis,
            proposal,
            tampered,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
        )
        self.assertEqual(validation["status"], "invalid_record")
        self.assertEqual(validation["reason"], "proposal_render_authorization_forbidden")

    def test_actor_and_reason_are_required(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        with self.assertRaisesRegex(ValueError, "actor"):
            build_execution_authorization(
                analysis,
                proposal,
                decision="APPROVE",
                actor=" ",
                reason="Reviewed.",
                analysis_sha256=ANALYSIS_SHA,
                proposal_sha256=PROPOSAL_SHA,
            )
        with self.assertRaisesRegex(ValueError, "reason"):
            build_execution_authorization(
                analysis,
                proposal,
                decision="APPROVE",
                actor="reviewer",
                reason=" ",
                analysis_sha256=ANALYSIS_SHA,
                proposal_sha256=PROPOSAL_SHA,
            )

    def test_blocked_proposal_cannot_receive_authorization(self):
        analysis = build_analysis()
        proposal = build_ready_proposal(analysis)
        proposal["status"] = "blocked_global_limits"
        proposal["proposed_edits"] = []
        with self.assertRaisesRegex(ValueError, "no está lista"):
            build_execution_authorization(
                analysis,
                proposal,
                decision="APPROVE",
                actor="reviewer",
                reason="Should fail.",
                analysis_sha256=ANALYSIS_SHA,
                proposal_sha256=PROPOSAL_SHA,
            )


if __name__ == "__main__":
    unittest.main()
