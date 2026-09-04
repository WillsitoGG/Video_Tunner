import copy
import tempfile
import unittest
from pathlib import Path

from video_tunner.approval import (
    build_approval_record,
    load_json_object,
    save_approval_record,
    validate_approval_record,
)


ANALYSIS_SHA = "a" * 64


def sample_analysis() -> dict:
    target = {
        "source": "candidate_word_span",
        "text": "proyecto central listo",
        "start": 1.0,
        "end": 1.8,
        "word_start_index": 1,
        "word_end_index_exclusive": 4,
    }
    return {
        "schema_version": 9,
        "candidates": [
            {
                "id": "possible_repetition-0001",
                "kind": "possible_repetition",
                "start": 1.0,
                "end": 1.8,
            }
        ],
        "eligibility_assessments": [
            {
                "id": "eligibility-assessment-0001",
                "candidate_id": "possible_repetition-0001",
                "candidate_kind": "possible_repetition",
                "status": "foundation_guards_pass",
                "future_promotion_candidate": True,
                "removed_text_validation": {
                    "valid": True,
                    **target,
                },
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


class ApprovalContractTests(unittest.TestCase):
    def test_approve_record_is_valid_but_never_edit_authorization(self):
        analysis = sample_analysis()
        record = build_approval_record(
            analysis,
            "promotion-assessment-0001",
            decision="approve",
            actor="Guille",
            reason="Repetición exacta revisada contra transcript y target.",
            analysis_sha256=ANALYSIS_SHA,
            created_utc="2026-09-04T17:20:00+00:00",
        )

        self.assertTrue(record["approved"])
        self.assertEqual(record["approval_state"], "approved")
        self.assertFalse(record["edit_plan_authorization"])
        self.assertIsNone(record["edit"])
        self.assertFalse(record["safe_for_cut"])
        self.assertFalse(record["executable"])
        self.assertFalse(record["auto_apply"])

        validation = validate_approval_record(
            analysis,
            record,
            analysis_sha256=ANALYSIS_SHA,
        )
        self.assertEqual(validation["status"], "valid_approved")
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["approved"])
        self.assertFalse(validation["edit_plan_authorization"])
        self.assertFalse(validation["executable"])

    def test_reject_record_is_valid_and_auditable(self):
        analysis = sample_analysis()
        record = build_approval_record(
            analysis,
            "promotion-assessment-0001",
            decision="REJECT",
            actor="reviewer-1",
            reason="La repetición es intencional en este contexto.",
            analysis_sha256=ANALYSIS_SHA,
        )
        validation = validate_approval_record(analysis, record, analysis_sha256=ANALYSIS_SHA)
        self.assertEqual(validation["status"], "valid_rejected")
        self.assertTrue(validation["valid"])
        self.assertFalse(validation["approved"])

    def test_changed_analysis_hash_marks_approval_stale(self):
        analysis = sample_analysis()
        record = build_approval_record(
            analysis,
            "promotion-assessment-0001",
            decision="APPROVE",
            actor="reviewer-1",
            reason="Revisado.",
            analysis_sha256=ANALYSIS_SHA,
        )
        validation = validate_approval_record(analysis, record, analysis_sha256="b" * 64)
        self.assertEqual(validation["status"], "stale_analysis")
        self.assertFalse(validation["valid"])
        self.assertFalse(validation["approved"])

    def test_changed_upstream_evidence_marks_approval_stale(self):
        analysis = sample_analysis()
        record = build_approval_record(
            analysis,
            "promotion-assessment-0001",
            decision="APPROVE",
            actor="reviewer-1",
            reason="Revisado.",
            analysis_sha256=ANALYSIS_SHA,
        )
        changed = copy.deepcopy(analysis)
        changed["promotion_assessments"][0]["mode"] = "aggressive"
        validation = validate_approval_record(changed, record, analysis_sha256=ANALYSIS_SHA)
        self.assertEqual(validation["status"], "stale_evidence")
        self.assertFalse(validation["valid"])
        self.assertFalse(validation["approved"])

    def test_upstream_blocked_promotion_cannot_receive_approval(self):
        analysis = sample_analysis()
        analysis["promotion_assessments"][0]["status"] = "blocked_upstream_eligibility"
        analysis["promotion_assessments"][0]["promotion_review_candidate"] = False
        with self.assertRaisesRegex(ValueError, "no es elegible"):
            build_approval_record(
                analysis,
                "promotion-assessment-0001",
                decision="APPROVE",
                actor="reviewer-1",
                reason="Intento inválido.",
                analysis_sha256=ANALYSIS_SHA,
            )

    def test_tampered_record_cannot_claim_edit_authorization(self):
        analysis = sample_analysis()
        record = build_approval_record(
            analysis,
            "promotion-assessment-0001",
            decision="APPROVE",
            actor="reviewer-1",
            reason="Revisado.",
            analysis_sha256=ANALYSIS_SHA,
        )
        record["edit_plan_authorization"] = True
        validation = validate_approval_record(analysis, record, analysis_sha256=ANALYSIS_SHA)
        self.assertEqual(validation["status"], "invalid_record")
        self.assertEqual(validation["reason"], "unexpected_edit_authorization")
        self.assertFalse(validation["valid"])
        self.assertFalse(validation["approved"])

    def test_decision_actor_and_reason_are_required(self):
        analysis = sample_analysis()
        common = {
            "analysis": analysis,
            "promotion_assessment_id": "promotion-assessment-0001",
            "analysis_sha256": ANALYSIS_SHA,
        }
        with self.assertRaisesRegex(ValueError, "APPROVE o REJECT"):
            build_approval_record(**common, decision="maybe", actor="reviewer", reason="x")
        with self.assertRaisesRegex(ValueError, "actor es obligatorio"):
            build_approval_record(**common, decision="APPROVE", actor=" ", reason="x")
        with self.assertRaisesRegex(ValueError, "reason es obligatorio"):
            build_approval_record(**common, decision="APPROVE", actor="reviewer", reason=" ")

    def test_save_and_load_roundtrip_preserves_fingerprint(self):
        analysis = sample_analysis()
        record = build_approval_record(
            analysis,
            "promotion-assessment-0001",
            decision="APPROVE",
            actor="reviewer-1",
            reason="Revisado.",
            analysis_sha256=ANALYSIS_SHA,
        )
        with tempfile.TemporaryDirectory() as temp:
            path = save_approval_record(record, Path(temp) / "approval.json")
            loaded = load_json_object(path)
        self.assertEqual(loaded["evidence_fingerprint"], record["evidence_fingerprint"])
        self.assertEqual(loaded["decision"], "APPROVE")


if __name__ == "__main__":
    unittest.main()
