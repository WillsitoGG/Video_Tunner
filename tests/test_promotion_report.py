import unittest

from video_tunner.promotion_report import attach_promotion_assessments, promotion_summary


class PromotionReportTests(unittest.TestCase):
    def test_summary_counts_review_candidates_without_creating_edits(self):
        assessments = [
            {
                "status": "eligible_for_promotion_review",
                "promotion_review_candidate": True,
                "approved": False,
                "edit": None,
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            },
            {
                "status": "blocked_upstream_eligibility",
                "promotion_review_candidate": False,
                "approved": False,
                "edit": None,
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            },
        ]
        summary = promotion_summary(assessments)
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["promotion_review_candidates"], 1)
        self.assertEqual(summary["approved"], 0)
        self.assertEqual(summary["edits"], 0)
        self.assertEqual(summary["safe_for_cut"], 0)
        self.assertEqual(summary["executable"], 0)
        self.assertEqual(summary["auto_apply"], 0)

    def test_attach_promotes_schema_only_not_edits(self):
        report = {
            "schema_version": 8,
            "summary": {},
            "safety": {},
        }
        assessments = [
            {
                "status": "eligible_for_promotion_review",
                "promotion_review_candidate": True,
                "approved": False,
                "edit": None,
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        ]
        attach_promotion_assessments(report, assessments)
        self.assertEqual(report["schema_version"], 9)
        self.assertEqual(report["promotion_assessments"], assessments)
        self.assertEqual(report["summary"]["promotion_assessments"]["approved"], 0)
        self.assertEqual(report["summary"]["promotion_assessments"]["edits"], 0)
        self.assertTrue(report["safety"]["promotion_assessments_are_not_edits"])
        self.assertTrue(report["safety"]["promotion_review_requires_explicit_approval"])
        self.assertFalse(report["safety"]["promotion_assessments_approved"])
        self.assertFalse(report["safety"]["edit_plan_promotion_enabled"])
        self.assertFalse(report["safety"]["promotion_assessments_executable"])
        self.assertFalse(report["safety"]["promotion_assessments_safe_for_cut"])


if __name__ == "__main__":
    unittest.main()
