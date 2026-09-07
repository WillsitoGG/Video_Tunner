import copy
import unittest

from video_tunner.normalization_approval import build_normalization_approval
from video_tunner.normalization_execution_authorization import (
    build_normalization_execution_authorization,
    validate_normalization_execution_authorization,
)
from video_tunner.normalization_plan import build_normalization_plan_proposal


QUALITY_SHA = "c" * 64
PROFILE_SHA = "d" * 64
APPROVAL_SHA = "e" * 64
PLAN_SHA = "1" * 64
OUTPUT_SHA = "a" * 64


def quality_audit(*, integrated=-30.0, true_peak=-10.0, lra=8.5, threshold=-40.0):
    return {
        "schema_version": 1,
        "record_type": "audiovisual_quality_audit",
        "status": "quality_audit_complete",
        "valid": True,
        "phase2e_binding": {
            "required_status": "technical_post_render_pass",
            "technical_report_sha256": "b" * 64,
            "source_sha256": "f" * 64,
            "output_sha256": OUTPUT_SHA,
            "join_count": 1,
        },
        "measurements": {
            "source_audio": {},
            "output_audio": {
                "integrated_lufs": integrated,
                "true_peak_dbtp": true_peak,
                "loudness_range_lu": lra,
                "threshold_lufs": threshold,
            },
            "delta": {},
        },
        "findings": [],
        "summary": {"finding_count": 0, "risk_count": 0, "quality_review_required": False},
        "treatment_policy": {},
        "treatment_authorized": False,
        "auto_apply": False,
    }


def profile_decision():
    return {
        "schema_version": 1,
        "record_type": "normalization_profile_decision",
        "status": "normalization_profile_review_selected",
        "quality_output_sha256": OUTPUT_SHA,
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


def chain(*, true_peak=-10.0):
    quality = quality_audit(true_peak=true_peak)
    profile = profile_decision()
    approval = build_normalization_approval(
        profile,
        decision="APPROVE",
        actor="Guille",
        reason="Prepare exact linear plan.",
        profile_decision_sha256=PROFILE_SHA,
        created_utc="2026-09-07T15:10:00+00:00",
    )
    plan = build_normalization_plan_proposal(
        quality,
        profile,
        approval,
        quality_audit_sha256=QUALITY_SHA,
        profile_decision_sha256=PROFILE_SHA,
        approval_sha256=APPROVAL_SHA,
    )
    return quality, profile, approval, plan


def authorize(quality, profile, approval, plan, *, decision="APPROVE"):
    return build_normalization_execution_authorization(
        quality,
        profile,
        approval,
        plan,
        decision=decision,
        actor="Guille",
        reason="Authorize only the gated normalization render path.",
        quality_audit_sha256=QUALITY_SHA,
        profile_decision_sha256=PROFILE_SHA,
        approval_sha256=APPROVAL_SHA,
        plan_sha256=PLAN_SHA,
        created_utc="2026-09-07T15:20:00+00:00",
    )


def validate(quality, profile, approval, plan, authorization, *, plan_sha=PLAN_SHA):
    return validate_normalization_execution_authorization(
        quality,
        profile,
        approval,
        plan,
        authorization,
        quality_audit_sha256=QUALITY_SHA,
        profile_decision_sha256=PROFILE_SHA,
        approval_sha256=APPROVAL_SHA,
        plan_sha256=plan_sha,
    )


class NormalizationExecutionAuthorizationTests(unittest.TestCase):
    def test_approve_authorizes_only_gated_normalization_render(self):
        quality, profile, approval, plan = chain()
        authorization = authorize(quality, profile, approval, plan)
        result = validate(quality, profile, approval, plan, authorization)
        self.assertEqual(result["status"], "valid_authorized")
        self.assertTrue(result["authorized"])
        self.assertTrue(result["normalization_render_authorization"])
        self.assertFalse(result["plan_render_authorization"])
        self.assertFalse(result["parameters_executable"])
        self.assertFalse(result["executable"])
        self.assertFalse(result["auto_apply"])

    def test_reject_is_valid_without_render_authorization(self):
        quality, profile, approval, plan = chain()
        authorization = authorize(quality, profile, approval, plan, decision="REJECT")
        result = validate(quality, profile, approval, plan, authorization)
        self.assertEqual(result["status"], "valid_rejected")
        self.assertTrue(result["valid"])
        self.assertFalse(result["authorized"])
        self.assertFalse(result["normalization_render_authorization"])

    def test_actor_and_reason_are_required(self):
        quality, profile, approval, plan = chain()
        kwargs = dict(
            decision="APPROVE",
            quality_audit_sha256=QUALITY_SHA,
            profile_decision_sha256=PROFILE_SHA,
            approval_sha256=APPROVAL_SHA,
            plan_sha256=PLAN_SHA,
        )
        with self.assertRaises(ValueError):
            build_normalization_execution_authorization(quality, profile, approval, plan, actor="", reason="x", **kwargs)
        with self.assertRaises(ValueError):
            build_normalization_execution_authorization(quality, profile, approval, plan, actor="Guille", reason="", **kwargs)

    def test_changed_plan_sha_marks_authorization_stale(self):
        quality, profile, approval, plan = chain()
        authorization = authorize(quality, profile, approval, plan)
        result = validate(quality, profile, approval, plan, authorization, plan_sha="2" * 64)
        self.assertEqual(result["status"], "stale_plan")
        self.assertFalse(result["authorized"])

    def test_tampered_plan_is_rebuilt_and_rejected(self):
        quality, profile, approval, plan = chain()
        authorization = authorize(quality, profile, approval, plan)
        tampered = copy.deepcopy(plan)
        tampered["targets"]["target_i"] = -14.0
        result = validate(quality, profile, approval, tampered, authorization)
        self.assertEqual(result["status"], "stale_or_invalid_plan")
        self.assertFalse(result["authorized"])

    def test_changed_upstream_measurement_invalidates_existing_plan_chain(self):
        quality, profile, approval, plan = chain()
        authorization = authorize(quality, profile, approval, plan)
        changed_quality = copy.deepcopy(quality)
        changed_quality["measurements"]["output_audio"]["integrated_lufs"] = -29.0
        result = validate(changed_quality, profile, approval, plan, authorization)
        self.assertEqual(result["status"], "stale_or_invalid_plan")
        self.assertFalse(result["authorized"])

    def test_blocked_plan_cannot_receive_execution_authorization(self):
        quality, profile, approval, plan = chain(true_peak=-2.0)
        self.assertEqual(plan["status"], "normalization_plan_blocked")
        with self.assertRaises(ValueError):
            authorize(quality, profile, approval, plan)

    def test_capability_tampering_is_rejected(self):
        quality, profile, approval, plan = chain()
        authorization = authorize(quality, profile, approval, plan)
        for field in ("plan_render_authorization", "parameters_executable", "executable", "auto_apply"):
            tampered = copy.deepcopy(authorization)
            tampered[field] = True
            result = validate(quality, profile, approval, plan, tampered)
            self.assertEqual(result["status"], "invalid_record")
            self.assertFalse(result["authorized"])


if __name__ == "__main__":
    unittest.main()
