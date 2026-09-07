import unittest

from video_tunner.normalization_approval import build_normalization_approval
from video_tunner.normalization_plan import build_normalization_plan_proposal


QUALITY_SHA = "c" * 64
PROFILE_SHA = "d" * 64
APPROVAL_SHA = "e" * 64
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


def approval(profile=None, *, decision="APPROVE"):
    profile = profile or profile_decision()
    return build_normalization_approval(
        profile,
        decision=decision,
        actor="Guille",
        reason="Prepare linear normalization plan for review.",
        profile_decision_sha256=PROFILE_SHA,
        created_utc="2026-09-07T15:10:00+00:00",
    )


class NormalizationPlanProposalTests(unittest.TestCase):
    def _build(self, audit):
        profile = profile_decision()
        return build_normalization_plan_proposal(
            audit,
            profile,
            approval(profile),
            quality_audit_sha256=QUALITY_SHA,
            profile_decision_sha256=PROFILE_SHA,
            approval_sha256=APPROVAL_SHA,
        )

    def test_feasible_linear_plan_preserves_measured_lra_without_render_capability(self):
        plan = self._build(quality_audit())
        self.assertEqual(plan["status"], "linear_normalization_plan_proposal_ready")
        self.assertTrue(plan["ready_for_render_gate_design"])
        self.assertEqual(plan["targets"]["target_i"], -23.0)
        self.assertEqual(plan["targets"]["target_tp"], -1.0)
        self.assertEqual(plan["targets"]["target_lra"], 8.5)
        self.assertEqual(plan["targets"]["calculated_linear_gain_lu"], 7.0)
        self.assertEqual(plan["targets"]["predicted_linear_true_peak_dbtp"], -3.0)
        self.assertEqual(plan["policy"]["lra_policy"], "preserve_measured_lra")
        self.assertFalse(plan["policy"]["dynamic_fallback_allowed"])
        self.assertTrue(plan["parameters_defined"])
        self.assertFalse(plan["parameters_executable"])
        self.assertFalse(plan["normalization_render_authorization"])
        self.assertFalse(plan["auto_apply"])

    def test_true_peak_constraint_blocks_instead_of_allowing_dynamic_fallback(self):
        plan = self._build(quality_audit(integrated=-30.0, true_peak=-2.0))
        self.assertEqual(plan["status"], "normalization_plan_blocked")
        self.assertFalse(plan["ready_for_render_gate_design"])
        self.assertIn("linear_true_peak_constraint_failed", [item["code"] for item in plan["blockers"]])
        self.assertFalse(plan["parameters_defined"])
        self.assertFalse(plan["normalization_authorized"])

    def test_lra_outside_ffmpeg_target_range_blocks(self):
        plan = self._build(quality_audit(lra=0.5))
        self.assertEqual(plan["status"], "normalization_plan_blocked")
        self.assertIn(
            "measured_lra_outside_ffmpeg_linear_target_range",
            [item["code"] for item in plan["blockers"]],
        )

    def test_ffmpeg_measured_i_sentinel_blocks_linear_plan(self):
        plan = self._build(quality_audit(integrated=0.0, true_peak=-30.0))
        self.assertEqual(plan["status"], "normalization_plan_blocked")
        self.assertIn("ffmpeg_linear_measured_i_sentinel", [item["code"] for item in plan["blockers"]])

    def test_ffmpeg_measured_thresh_sentinel_blocks_linear_plan(self):
        plan = self._build(quality_audit(threshold=-70.0))
        self.assertEqual(plan["status"], "normalization_plan_blocked")
        self.assertIn("ffmpeg_linear_measured_thresh_sentinel", [item["code"] for item in plan["blockers"]])

    def test_rejected_approval_cannot_build_plan(self):
        profile = profile_decision()
        with self.assertRaises(ValueError):
            build_normalization_plan_proposal(
                quality_audit(),
                profile,
                approval(profile, decision="REJECT"),
                quality_audit_sha256=QUALITY_SHA,
                profile_decision_sha256=PROFILE_SHA,
                approval_sha256=APPROVAL_SHA,
            )

    def test_profile_and_quality_output_sha_must_match(self):
        profile = profile_decision()
        approved = approval(profile)
        changed = profile_decision()
        changed["quality_output_sha256"] = "9" * 64
        with self.assertRaises(ValueError):
            build_normalization_plan_proposal(
                quality_audit(),
                changed,
                approved,
                quality_audit_sha256=QUALITY_SHA,
                profile_decision_sha256=PROFILE_SHA,
                approval_sha256=APPROVAL_SHA,
            )

    def test_missing_finite_measurement_fails_closed(self):
        profile = profile_decision()
        with self.assertRaises(ValueError):
            build_normalization_plan_proposal(
                quality_audit(lra=None),
                profile,
                approval(profile),
                quality_audit_sha256=QUALITY_SHA,
                profile_decision_sha256=PROFILE_SHA,
                approval_sha256=APPROVAL_SHA,
            )

    def test_approval_sha_is_required_for_provenance(self):
        profile = profile_decision()
        with self.assertRaises(ValueError):
            build_normalization_plan_proposal(
                quality_audit(),
                profile,
                approval(profile),
                quality_audit_sha256=QUALITY_SHA,
                profile_decision_sha256=PROFILE_SHA,
                approval_sha256="invalid",
            )


if __name__ == "__main__":
    unittest.main()
