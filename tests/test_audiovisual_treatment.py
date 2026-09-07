import unittest

from video_tunner.audiovisual_treatment import build_audiovisual_treatment_decision


OUTPUT_SHA = "a" * 64
TECHNICAL_SHA = "b" * 64


def audit(*, findings=None, risk_count=None):
    findings = [] if findings is None else findings
    if risk_count is None:
        risk_count = sum(item.get("severity") == "risk" for item in findings)
    return {
        "schema_version": 1,
        "record_type": "audiovisual_quality_audit",
        "status": "quality_audit_complete",
        "valid": True,
        "phase2e_binding": {
            "required_status": "technical_post_render_pass",
            "technical_report_sha256": TECHNICAL_SHA,
            "source_sha256": "c" * 64,
            "output_sha256": OUTPUT_SHA,
            "join_count": 1,
        },
        "measurements": {},
        "findings": findings,
        "summary": {
            "finding_count": len(findings),
            "risk_count": risk_count,
            "quality_review_required": bool(findings),
        },
        "treatment_policy": {},
        "treatment_authorized": False,
        "auto_apply": False,
    }


class AudiovisualTreatmentDecisionTests(unittest.TestCase):
    def test_clean_audit_bypasses_and_preserves_render(self):
        decision = build_audiovisual_treatment_decision(audit())
        self.assertEqual(decision["status"], "bypass_preserve_render")
        self.assertFalse(decision["review_required"])
        self.assertEqual(decision["review_topics"], [])
        self.assertFalse(decision["treatment_policy"]["parameters_defined"])
        self.assertFalse(decision["treatment_policy"]["mandatory_treatment"])
        self.assertFalse(decision["executable"])
        self.assertFalse(decision["treatment_authorized"])
        self.assertFalse(decision["auto_apply"])

    def test_true_peak_risk_requests_policy_review_but_never_authorizes_treatment(self):
        decision = build_audiovisual_treatment_decision(
            audit(
                findings=[
                    {
                        "code": "output_true_peak_above_0_dbtp",
                        "severity": "risk",
                    }
                ]
            )
        )
        self.assertEqual(decision["status"], "treatment_review_required")
        self.assertTrue(decision["review_required"])
        self.assertEqual(
            decision["review_topics"],
            ["evaluate_normalization_or_true_peak_policy"],
        )
        self.assertEqual(decision["treatment_policy"]["normalization"], "not_authorized")
        self.assertFalse(decision["treatment_authorized"])
        self.assertFalse(decision["auto_apply"])

    def test_unknown_risk_fails_safe_to_manual_quality_review(self):
        decision = build_audiovisual_treatment_decision(
            audit(findings=[{"code": "future_risk", "severity": "risk"}])
        )
        self.assertEqual(decision["status"], "treatment_review_required")
        self.assertEqual(decision["review_topics"], ["manual_audiovisual_quality_review"])
        self.assertFalse(decision["executable"])

    def test_risk_count_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            build_audiovisual_treatment_decision(
                audit(findings=[{"code": "future_risk", "severity": "risk"}], risk_count=0)
            )

    def test_upstream_audit_cannot_smuggle_treatment_capability(self):
        payload = audit()
        payload["treatment_authorized"] = True
        with self.assertRaises(ValueError):
            build_audiovisual_treatment_decision(payload)

    def test_invalid_or_stale_phase2e_binding_is_rejected(self):
        payload = audit()
        payload["phase2e_binding"]["output_sha256"] = "stale"
        with self.assertRaises(ValueError):
            build_audiovisual_treatment_decision(payload)


if __name__ == "__main__":
    unittest.main()
