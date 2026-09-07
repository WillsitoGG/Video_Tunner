import unittest

from video_tunner.normalization_approval import (
    build_normalization_approval,
    validate_normalization_approval,
)


PROFILE_SHA = "d" * 64


def profile_decision():
    return {
        "schema_version": 1,
        "record_type": "normalization_profile_decision",
        "status": "normalization_profile_review_selected",
        "quality_output_sha256": "a" * 64,
        "profile": {
            "name": "ebu_r128_programme",
            "description": "review-only",
            "target_lufs": -23.0,
            "max_true_peak_dbtp": -1.0,
            "standard": "EBU R 128",
            "standard_version": "5.0 (November 2023)",
            "measurement_basis": "ITU-R BS.1770-5 (November 2023)",
            "treatment_requested": True,
        },
        "explicit_opt_in_required": True,
        "human_approval_required": True,
        "normalization_requested": True,
        "normalization_authorized": False,
        "parameters_executable": False,
        "render_authorized": False,
        "auto_apply": False,
    }


class NormalizationApprovalTests(unittest.TestCase):
    def test_approve_is_valid_but_only_authorizes_next_plan_gate(self):
        profile = profile_decision()
        approval = build_normalization_approval(
            profile,
            decision="APPROVE",
            actor="Guille",
            reason="Explicitly review this standards-based profile.",
            profile_decision_sha256=PROFILE_SHA,
            created_utc="2026-09-07T15:00:00+00:00",
        )
        self.assertTrue(approval["approved"])
        self.assertTrue(approval["normalization_plan_preparation_authorized"])
        self.assertFalse(approval["normalization_authorized"])
        self.assertFalse(approval["normalization_render_authorization"])
        self.assertFalse(approval["parameters_executable"])
        self.assertFalse(approval["executable"])
        self.assertFalse(approval["auto_apply"])

        validation = validate_normalization_approval(
            profile,
            approval,
            profile_decision_sha256=PROFILE_SHA,
        )
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "valid_approved")
        self.assertTrue(validation["normalization_plan_preparation_authorized"])
        self.assertFalse(validation["normalization_render_authorization"])

    def test_reject_is_valid_and_has_no_preparation_capability(self):
        profile = profile_decision()
        approval = build_normalization_approval(
            profile,
            decision="REJECT",
            actor="Guille",
            reason="Do not normalize this output.",
            profile_decision_sha256=PROFILE_SHA,
        )
        validation = validate_normalization_approval(
            profile,
            approval,
            profile_decision_sha256=PROFILE_SHA,
        )
        self.assertTrue(validation["valid"])
        self.assertEqual(validation["status"], "valid_rejected")
        self.assertFalse(validation["approved"])
        self.assertFalse(validation["normalization_plan_preparation_authorized"])

    def test_profile_file_sha_change_marks_approval_stale(self):
        profile = profile_decision()
        approval = build_normalization_approval(
            profile,
            decision="APPROVE",
            actor="Guille",
            reason="Review profile.",
            profile_decision_sha256=PROFILE_SHA,
        )
        validation = validate_normalization_approval(
            profile,
            approval,
            profile_decision_sha256="e" * 64,
        )
        self.assertFalse(validation["valid"])
        self.assertEqual(validation["status"], "stale_profile_decision")

    def test_profile_snapshot_change_marks_approval_stale(self):
        profile = profile_decision()
        approval = build_normalization_approval(
            profile,
            decision="APPROVE",
            actor="Guille",
            reason="Review profile.",
            profile_decision_sha256=PROFILE_SHA,
        )
        changed = profile_decision()
        changed["profile"]["target_lufs"] = -22.0
        validation = validate_normalization_approval(
            changed,
            approval,
            profile_decision_sha256=PROFILE_SHA,
        )
        self.assertFalse(validation["valid"])
        self.assertEqual(validation["status"], "stale_profile_decision")

    def test_preserve_profile_cannot_receive_normalization_approval(self):
        profile = profile_decision()
        profile["status"] = "preserve_selected"
        profile["profile"]["name"] = "preserve"
        profile["explicit_opt_in_required"] = False
        profile["human_approval_required"] = False
        profile["normalization_requested"] = False
        with self.assertRaises(ValueError):
            build_normalization_approval(
                profile,
                decision="APPROVE",
                actor="Guille",
                reason="Meaningless approval should fail.",
                profile_decision_sha256=PROFILE_SHA,
            )

    def test_actor_and_reason_are_mandatory(self):
        profile = profile_decision()
        with self.assertRaises(ValueError):
            build_normalization_approval(
                profile,
                decision="APPROVE",
                actor="",
                reason="reason",
                profile_decision_sha256=PROFILE_SHA,
            )
        with self.assertRaises(ValueError):
            build_normalization_approval(
                profile,
                decision="APPROVE",
                actor="Guille",
                reason="",
                profile_decision_sha256=PROFILE_SHA,
            )

    def test_tampered_render_capability_is_rejected(self):
        profile = profile_decision()
        approval = build_normalization_approval(
            profile,
            decision="APPROVE",
            actor="Guille",
            reason="Review profile.",
            profile_decision_sha256=PROFILE_SHA,
        )
        approval["normalization_render_authorization"] = True
        validation = validate_normalization_approval(
            profile,
            approval,
            profile_decision_sha256=PROFILE_SHA,
        )
        self.assertFalse(validation["valid"])
        self.assertEqual(validation["reason"], "unexpected_execution_capability")

    def test_decision_state_tampering_is_rejected(self):
        profile = profile_decision()
        approval = build_normalization_approval(
            profile,
            decision="REJECT",
            actor="Guille",
            reason="Reject profile.",
            profile_decision_sha256=PROFILE_SHA,
        )
        approval["approved"] = True
        validation = validate_normalization_approval(
            profile,
            approval,
            profile_decision_sha256=PROFILE_SHA,
        )
        self.assertFalse(validation["valid"])
        self.assertEqual(validation["reason"], "decision_approved_mismatch")


if __name__ == "__main__":
    unittest.main()
