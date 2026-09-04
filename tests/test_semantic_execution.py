import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.approval import build_approval_record
from video_tunner.execution_authorization import build_execution_authorization
from video_tunner.plan_proposal import build_approved_edit_plan_proposal
from video_tunner.render import render_from_plan
from video_tunner.semantic_edit_plan import (
    build_semantic_edit_plan,
    validate_semantic_edit_plan,
)
from video_tunner.semantic_render import (
    render_semantic_plan,
    validate_semantic_render_request,
)


ANALYSIS_SHA = "a" * 64
PROPOSAL_SHA = "c" * 64
AUTHORIZATION_SHA = "d" * 64


def build_analysis(source_sha="b" * 64):
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
        "source": {"file": "video.mp4", "duration_seconds": 100.0, "sha256": source_sha},
        "mode": "conservative",
        "candidates": [{"id": "possible_repetition-0001", "kind": "possible_repetition", "start": 10.0, "end": 11.0}],
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


def build_chain(source_sha="b" * 64, *, execution_decision="APPROVE"):
    analysis = build_analysis(source_sha)
    approval = build_approval_record(
        analysis,
        "promotion-assessment-0001",
        decision="APPROVE",
        actor="candidate-reviewer",
        reason="Exact repetition reviewed.",
        analysis_sha256=ANALYSIS_SHA,
    )
    proposal = build_approved_edit_plan_proposal(
        analysis,
        [approval],
        analysis_sha256=ANALYSIS_SHA,
    )
    authorization = build_execution_authorization(
        analysis,
        proposal,
        decision=execution_decision,
        actor="global-reviewer",
        reason="Whole bounded proposal reviewed.",
        analysis_sha256=ANALYSIS_SHA,
        proposal_sha256=PROPOSAL_SHA,
    )
    return analysis, proposal, authorization


def build_plan(source_sha="b" * 64):
    analysis, proposal, authorization = build_chain(source_sha)
    plan = build_semantic_edit_plan(
        analysis,
        proposal,
        authorization,
        analysis_sha256=ANALYSIS_SHA,
        proposal_sha256=PROPOSAL_SHA,
        authorization_sha256=AUTHORIZATION_SHA,
    )
    return analysis, proposal, authorization, plan


class SemanticExecutionTests(unittest.TestCase):
    def test_valid_authorization_materializes_exact_executable_plan_but_not_auto_apply(self):
        analysis, proposal, authorization, plan = build_plan()
        self.assertEqual(plan["record_type"], "semantic_edit_plan")
        self.assertNotIn("proposed_edits", plan)
        self.assertEqual(len(plan["edits"]), 1)
        self.assertEqual(plan["edits"][0]["action"], "remove")
        self.assertEqual(plan["edits"][0]["start"], 10.0)
        self.assertEqual(plan["edits"][0]["end"], 11.0)
        self.assertTrue(plan["globally_authorized"])
        self.assertTrue(plan["requires_semantic_render_gate"])
        self.assertTrue(plan["executable"])
        self.assertFalse(plan["auto_apply"])

        validation = validate_semantic_edit_plan(
            analysis,
            proposal,
            authorization,
            plan,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
            authorization_sha256=AUTHORIZATION_SHA,
        )
        self.assertEqual(validation["status"], "valid_semantic_edit_plan")
        self.assertTrue(validation["render_gate_ready"])

    def test_rejected_global_authorization_cannot_materialize_plan(self):
        analysis, proposal, authorization = build_chain(execution_decision="REJECT")
        with self.assertRaisesRegex(ValueError, "valid_rejected"):
            build_semantic_edit_plan(
                analysis,
                proposal,
                authorization,
                analysis_sha256=ANALYSIS_SHA,
                proposal_sha256=PROPOSAL_SHA,
                authorization_sha256=AUTHORIZATION_SHA,
            )

    def test_tampered_plan_edit_is_detected(self):
        analysis, proposal, authorization, plan = build_plan()
        tampered = copy.deepcopy(plan)
        tampered["edits"][0]["end"] = 11.5
        validation = validate_semantic_edit_plan(
            analysis,
            proposal,
            authorization,
            tampered,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
            authorization_sha256=AUTHORIZATION_SHA,
        )
        self.assertEqual(validation["status"], "stale_or_tampered_plan")
        self.assertFalse(validation["render_gate_ready"])

    def test_changed_authorization_hash_invalidates_materialized_plan(self):
        analysis, proposal, authorization, plan = build_plan()
        validation = validate_semantic_edit_plan(
            analysis,
            proposal,
            authorization,
            plan,
            analysis_sha256=ANALYSIS_SHA,
            proposal_sha256=PROPOSAL_SHA,
            authorization_sha256="e" * 64,
        )
        self.assertEqual(validation["status"], "stale_or_tampered_plan")
        self.assertFalse(validation["render_gate_ready"])

    def test_generic_renderer_rejects_semantic_edit_plan(self):
        _, _, _, plan = build_plan()
        with self.assertRaisesRegex(ValueError, "Semantic Edit Plan"):
            render_from_plan("input.mp4", plan, "output.mp4")

    def test_semantic_render_gate_rejects_source_sha_mismatch(self):
        analysis, proposal, authorization, plan = build_plan()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "video.mp4"
            source.write_bytes(b"different-source")
            validation = validate_semantic_render_request(
                source,
                analysis,
                proposal,
                authorization,
                plan,
                analysis_sha256=ANALYSIS_SHA,
                proposal_sha256=PROPOSAL_SHA,
                authorization_sha256=AUTHORIZATION_SHA,
            )
        self.assertEqual(validation["status"], "blocked_source_mismatch")
        self.assertEqual(validation["reason"], "source_sha256_changed")
        self.assertFalse(validation["render_authorized"])

    def test_valid_semantic_render_gate_revalidates_chain_before_renderer(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "video.mp4"
            source.write_bytes(b"exact-source-bytes")
            source_sha = hashlib.sha256(source.read_bytes()).hexdigest()
            analysis, proposal, authorization, plan = build_plan(source_sha)
            destination = Path(temp) / "clean.mp4"

            validation = validate_semantic_render_request(
                source,
                analysis,
                proposal,
                authorization,
                plan,
                analysis_sha256=ANALYSIS_SHA,
                proposal_sha256=PROPOSAL_SHA,
                authorization_sha256=AUTHORIZATION_SHA,
            )
            self.assertEqual(validation["status"], "valid_semantic_render_request")
            self.assertTrue(validation["render_authorized"])
            self.assertFalse(validation["auto_apply"])

            with patch("video_tunner.semantic_render.render_from_plan", return_value=destination) as mocked:
                result = render_semantic_plan(
                    source,
                    analysis,
                    proposal,
                    authorization,
                    plan,
                    destination,
                    analysis_sha256=ANALYSIS_SHA,
                    proposal_sha256=PROPOSAL_SHA,
                    authorization_sha256=AUTHORIZATION_SHA,
                )
            self.assertEqual(result, destination)
            mocked.assert_called_once()
            self.assertTrue(mocked.call_args.kwargs["semantic_gate_authorized"])


if __name__ == "__main__":
    unittest.main()
