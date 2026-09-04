import copy
import unittest

from video_tunner.human_render_review import (
    build_human_render_review,
    validate_human_render_review,
)


REPORT_SHA = "a" * 64


def technical_report():
    return {
        "schema_version": 1,
        "record_type": "semantic_render_verification",
        "status": "technical_post_render_pass",
        "technical_pass": True,
        "blockers": [],
        "execution_chain": {
            "plan_fingerprint": "b" * 64,
        },
        "output": {
            "sha256": "c" * 64,
        },
        "post_render_join_audits": [
            {
                "id": "post-render-join-0001",
                "edit_id": "semantic-edit-0001",
                "candidate_id": "possible_repetition-0001",
                "output_join_seconds": 2.0,
                "status": "acoustic_context_only",
                "technical_pass": True,
            },
            {
                "id": "post-render-join-0002",
                "edit_id": "semantic-edit-0002",
                "candidate_id": "possible_repetition-0002",
                "output_join_seconds": 7.5,
                "status": "low_energy_boundary_context",
                "technical_pass": True,
            },
        ],
        "auto_apply": False,
    }


def pass_decisions():
    return [
        {
            "join_id": "post-render-join-0001",
            "decision": "PASS",
            "reason": "No audible click, truncation or unnatural timing.",
        },
        {
            "join_id": "post-render-join-0002",
            "decision": "PASS",
            "reason": "Join sounds natural and preserves intended speech.",
        },
    ]


class HumanRenderReviewTests(unittest.TestCase):
    def test_all_human_passes_close_one_render_but_not_phase2e(self):
        report = technical_report()
        review = build_human_render_review(
            report,
            pass_decisions(),
            actor="human-reviewer",
            reason="Listened to all semantic joins with headphones.",
            technical_report_sha256=REPORT_SHA,
            created_utc="2026-09-04T20:00:00+00:00",
        )
        self.assertEqual(review["status"], "human_perceptual_pass")
        self.assertTrue(review["human_perceptual_pass"])
        self.assertTrue(review["render_closeout_ready"])
        self.assertFalse(review["phase2e_closeout_ready"])
        self.assertTrue(review["requires_phase2e_corpus_closeout"])
        self.assertFalse(review["auto_apply"])

        validation = validate_human_render_review(
            report,
            review,
            technical_report_sha256=REPORT_SHA,
        )
        self.assertEqual(validation["status"], "valid_human_pass")
        self.assertTrue(validation["valid"])
        self.assertTrue(validation["render_closeout_ready"])
        self.assertFalse(validation["phase2e_closeout_ready"])

    def test_one_human_fail_fails_render_review(self):
        report = technical_report()
        decisions = pass_decisions()
        decisions[1] = {
            "join_id": "post-render-join-0002",
            "decision": "FAIL",
            "reason": "Audible click at the join.",
        }
        review = build_human_render_review(
            report,
            decisions,
            actor="human-reviewer",
            reason="One join is perceptually unacceptable.",
            technical_report_sha256=REPORT_SHA,
        )
        self.assertEqual(review["status"], "human_perceptual_failed")
        self.assertFalse(review["render_closeout_ready"])
        validation = validate_human_render_review(
            report,
            review,
            technical_report_sha256=REPORT_SHA,
        )
        self.assertEqual(validation["status"], "valid_human_fail")
        self.assertFalse(validation["human_perceptual_pass"])

    def test_every_join_requires_exactly_one_human_decision(self):
        report = technical_report()
        with self.assertRaisesRegex(ValueError, "exactamente todos"):
            build_human_render_review(
                report,
                pass_decisions()[:1],
                actor="reviewer",
                reason="Incomplete.",
                technical_report_sha256=REPORT_SHA,
            )

    def test_unknown_or_duplicate_join_is_rejected(self):
        report = technical_report()
        unknown = pass_decisions()
        unknown[1]["join_id"] = "post-render-join-9999"
        with self.assertRaisesRegex(ValueError, "desconocido"):
            build_human_render_review(
                report,
                unknown,
                actor="reviewer",
                reason="Invalid.",
                technical_report_sha256=REPORT_SHA,
            )

        duplicate = pass_decisions()
        duplicate[1]["join_id"] = "post-render-join-0001"
        with self.assertRaisesRegex(ValueError, "duplicado"):
            build_human_render_review(
                report,
                duplicate,
                actor="reviewer",
                reason="Invalid.",
                technical_report_sha256=REPORT_SHA,
            )

    def test_stale_technical_report_hash_invalidates_review(self):
        report = technical_report()
        review = build_human_render_review(
            report,
            pass_decisions(),
            actor="reviewer",
            reason="Reviewed.",
            technical_report_sha256=REPORT_SHA,
        )
        validation = validate_human_render_review(
            report,
            review,
            technical_report_sha256="d" * 64,
        )
        self.assertEqual(validation["status"], "stale_verification")
        self.assertFalse(validation["valid"])

    def test_changed_output_or_plan_invalidates_review(self):
        report = technical_report()
        review = build_human_render_review(
            report,
            pass_decisions(),
            actor="reviewer",
            reason="Reviewed.",
            technical_report_sha256=REPORT_SHA,
        )
        changed_output = copy.deepcopy(report)
        changed_output["output"]["sha256"] = "e" * 64
        validation = validate_human_render_review(
            changed_output,
            review,
            technical_report_sha256=REPORT_SHA,
        )
        self.assertEqual(validation["status"], "stale_verification")

        changed_plan = copy.deepcopy(report)
        changed_plan["execution_chain"]["plan_fingerprint"] = "f" * 64
        validation = validate_human_render_review(
            changed_plan,
            review,
            technical_report_sha256=REPORT_SHA,
        )
        self.assertEqual(validation["status"], "stale_verification")

    def test_changed_join_snapshot_invalidates_review(self):
        report = technical_report()
        review = build_human_render_review(
            report,
            pass_decisions(),
            actor="reviewer",
            reason="Reviewed.",
            technical_report_sha256=REPORT_SHA,
        )
        changed = copy.deepcopy(report)
        changed["post_render_join_audits"][0]["output_join_seconds"] = 2.1
        validation = validate_human_render_review(
            changed,
            review,
            technical_report_sha256=REPORT_SHA,
        )
        self.assertEqual(validation["status"], "stale_verification")
        self.assertIn("join_snapshot_changed", validation["reason"])

    def test_human_review_cannot_be_built_on_technical_failure(self):
        report = technical_report()
        report["technical_pass"] = False
        report["status"] = "technical_post_render_failed"
        with self.assertRaisesRegex(ValueError, "gate técnico PASS"):
            build_human_render_review(
                report,
                pass_decisions(),
                actor="reviewer",
                reason="Should fail.",
                technical_report_sha256=REPORT_SHA,
            )

    def test_actor_reason_and_per_join_reason_are_mandatory(self):
        report = technical_report()
        with self.assertRaisesRegex(ValueError, "actor"):
            build_human_render_review(
                report,
                pass_decisions(),
                actor=" ",
                reason="Reviewed.",
                technical_report_sha256=REPORT_SHA,
            )
        decisions = pass_decisions()
        decisions[0]["reason"] = " "
        with self.assertRaisesRegex(ValueError, "reason"):
            build_human_render_review(
                report,
                decisions,
                actor="reviewer",
                reason="Reviewed.",
                technical_report_sha256=REPORT_SHA,
            )


if __name__ == "__main__":
    unittest.main()
