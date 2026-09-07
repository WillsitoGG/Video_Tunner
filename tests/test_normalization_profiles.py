import unittest

from video_tunner.normalization_profiles import (
    DEFAULT_NORMALIZATION_PROFILE,
    EBU_R128_PROGRAMME_PROFILE,
    build_normalization_profile_decision,
    normalization_profile,
)


def treatment_decision(*, status="bypass_preserve_render", risk_count=0):
    return {
        "schema_version": 1,
        "record_type": "audiovisual_treatment_decision",
        "status": status,
        "quality_audit_binding": {
            "output_sha256": "a" * 64,
            "technical_report_sha256": "b" * 64,
            "risk_count": risk_count,
        },
        "review_required": bool(risk_count),
        "review_topics": [],
        "treatment_policy": {
            "normalization": "not_authorized",
            "denoise": "not_authorized",
            "join_smoothing": "not_authorized",
            "parameters_defined": False,
            "mandatory_treatment": False,
        },
        "executable": False,
        "treatment_authorized": False,
        "auto_apply": False,
    }


class NormalizationProfileTests(unittest.TestCase):
    def test_product_default_is_preserve(self):
        self.assertEqual(DEFAULT_NORMALIZATION_PROFILE, "preserve")
        profile = normalization_profile(DEFAULT_NORMALIZATION_PROFILE)
        self.assertIsNone(profile["target_lufs"])
        self.assertIsNone(profile["max_true_peak_dbtp"])
        self.assertFalse(profile["treatment_requested"])

    def test_ebu_r128_profile_records_current_standard_targets(self):
        profile = normalization_profile(EBU_R128_PROGRAMME_PROFILE)
        self.assertEqual(profile["target_lufs"], -23.0)
        self.assertEqual(profile["max_true_peak_dbtp"], -1.0)
        self.assertEqual(profile["standard"], "EBU R 128")
        self.assertEqual(profile["standard_version"], "5.0 (November 2023)")
        self.assertEqual(profile["measurement_basis"], "ITU-R BS.1770-5 (November 2023)")
        self.assertTrue(profile["treatment_requested"])

    def test_preserve_decision_never_requests_or_authorizes_normalization(self):
        decision = build_normalization_profile_decision(treatment_decision())
        self.assertEqual(decision["status"], "preserve_selected")
        self.assertFalse(decision["normalization_requested"])
        self.assertFalse(decision["human_approval_required"])
        self.assertFalse(decision["normalization_authorized"])
        self.assertFalse(decision["parameters_executable"])
        self.assertFalse(decision["render_authorized"])
        self.assertFalse(decision["auto_apply"])

    def test_ebu_r128_is_explicit_opt_in_review_only(self):
        decision = build_normalization_profile_decision(
            treatment_decision(),
            profile_name=EBU_R128_PROGRAMME_PROFILE,
        )
        self.assertEqual(decision["status"], "normalization_profile_review_selected")
        self.assertTrue(decision["explicit_opt_in_required"])
        self.assertTrue(decision["human_approval_required"])
        self.assertTrue(decision["normalization_requested"])
        self.assertFalse(decision["normalization_authorized"])
        self.assertFalse(decision["parameters_executable"])
        self.assertFalse(decision["render_authorized"])
        self.assertFalse(decision["auto_apply"])

    def test_measured_risk_never_auto_selects_ebu_profile(self):
        decision = build_normalization_profile_decision(
            treatment_decision(status="treatment_review_required", risk_count=1)
        )
        self.assertEqual(decision["profile"]["name"], "preserve")
        self.assertFalse(decision["normalization_requested"])
        self.assertFalse(decision["normalization_authorized"])

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            build_normalization_profile_decision(
                treatment_decision(),
                profile_name="youtube_magic_number",
            )

    def test_upstream_executable_capability_is_rejected(self):
        payload = treatment_decision()
        payload["executable"] = True
        with self.assertRaises(ValueError):
            build_normalization_profile_decision(payload)


if __name__ == "__main__":
    unittest.main()
