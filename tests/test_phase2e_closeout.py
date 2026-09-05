import copy
import unittest

from video_tunner.human_render_review import build_human_render_review
from video_tunner.phase2e_closeout import build_phase2e_closeout_decision


CASE_IDS = ["case-1", "case-2", "case-3"]
REPORT_SHAS = {
    "case-1": "1" * 64,
    "case-2": "2" * 64,
    "case-3": "3" * 64,
}


def manifest():
    return {
        "schema_version": 1,
        "record_type": "phase2e_human_render_review_bundle",
        "selection_locked_before_listening": True,
        "pre_human_gate": "PASS",
        "closeout_policy": {
            "minimum_rendered_human_cases": 3,
            "minimum_distinct_audio_sources": 2,
            "required_technical_pass_fraction": 1.0,
            "required_human_perceptual_pass_fraction": 1.0,
            "maximum_safety_violations": 0,
            "decision_if_all_pass": "CLOSE_OUT_READY",
            "decision_if_any_fail": "INSUFFICIENT_JOIN_QUALITY",
        },
        "cases": [
            {"id": "case-1", "audio_source_id": "source-a"},
            {"id": "case-2", "audio_source_id": "source-b"},
            {"id": "case-3", "audio_source_id": "source-a"},
        ],
    }


def technical_report(case_id: str):
    index = CASE_IDS.index(case_id) + 1
    return {
        "schema_version": 1,
        "record_type": "semantic_render_verification",
        "status": "technical_post_render_pass",
        "technical_pass": True,
        "blockers": [],
        "execution_chain": {"plan_fingerprint": f"{index + 3:x}" * 64},
        "output": {"sha256": f"{index + 6:x}" * 64},
        "post_render_join_audits": [
            {
                "id": "post-render-join-0001",
                "edit_id": "semantic-edit-0001",
                "candidate_id": f"candidate-{index}",
                "output_join_seconds": float(index),
                "status": "acoustic_context_only",
                "technical_pass": True,
            }
        ],
        "auto_apply": False,
    }


def evidence(*, failing_case: str | None = None):
    reports = {case_id: technical_report(case_id) for case_id in CASE_IDS}
    reviews = {}
    for case_id, report in reports.items():
        decision = "FAIL" if case_id == failing_case else "PASS"
        reviews[case_id] = build_human_render_review(
            report,
            [
                {
                    "join_id": "post-render-join-0001",
                    "decision": decision,
                    "reason": "Audible defect." if decision == "FAIL" else "Natural join with no audible defect.",
                }
            ],
            actor="human-reviewer",
            reason="Listened to the full precommitted closeout case.",
            technical_report_sha256=REPORT_SHAS[case_id],
            created_utc="2026-09-05T09:00:00+00:00",
        )
    return reports, reviews


class Phase2ECloseoutTests(unittest.TestCase):
    def test_three_valid_human_passes_across_two_sources_close_phase2e(self):
        reports, reviews = evidence()
        result = build_phase2e_closeout_decision(
            manifest(), reports, reviews, technical_report_sha256=REPORT_SHAS
        )
        self.assertEqual(result["status"], "CLOSE_OUT_READY")
        self.assertTrue(result["phase2e_closeout_ready"])
        self.assertFalse(result["auto_apply"])
        self.assertEqual(result["summary"]["human_perceptual_pass_count"], 3)

    def test_one_human_fail_keeps_phase2e_open(self):
        reports, reviews = evidence(failing_case="case-2")
        result = build_phase2e_closeout_decision(
            manifest(), reports, reviews, technical_report_sha256=REPORT_SHAS
        )
        self.assertEqual(result["status"], "INSUFFICIENT_JOIN_QUALITY")
        self.assertFalse(result["phase2e_closeout_ready"])
        self.assertEqual(result["summary"]["human_perceptual_fail_count"], 1)

    def test_stale_review_is_invalid_evidence_not_a_quality_fail(self):
        reports, reviews = evidence()
        stale_shas = dict(REPORT_SHAS)
        stale_shas["case-1"] = "f" * 64
        result = build_phase2e_closeout_decision(
            manifest(), reports, reviews, technical_report_sha256=stale_shas
        )
        self.assertEqual(result["status"], "INVALID_EVIDENCE")
        self.assertFalse(result["phase2e_closeout_ready"])
        self.assertEqual(result["summary"]["invalid_or_stale_review_count"], 1)

    def test_post_hoc_policy_relaxation_is_rejected(self):
        reports, reviews = evidence()
        relaxed = copy.deepcopy(manifest())
        relaxed["closeout_policy"]["required_human_perceptual_pass_fraction"] = 2 / 3
        result = build_phase2e_closeout_decision(
            relaxed, reports, reviews, technical_report_sha256=REPORT_SHAS
        )
        self.assertEqual(result["status"], "INVALID_EVIDENCE")
        self.assertIn("closeout_policy_changed", result["reason"])

    def test_two_source_requirement_cannot_be_bypassed(self):
        reports, reviews = evidence()
        one_source = copy.deepcopy(manifest())
        for case in one_source["cases"]:
            case["audio_source_id"] = "source-a"
        result = build_phase2e_closeout_decision(
            one_source, reports, reviews, technical_report_sha256=REPORT_SHAS
        )
        self.assertEqual(result["status"], "INVALID_EVIDENCE")
        self.assertEqual(result["reason"], "distinct_source_count_below_locked_minimum")


if __name__ == "__main__":
    unittest.main()
