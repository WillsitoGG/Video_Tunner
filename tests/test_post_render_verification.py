import copy
import unittest
from unittest.mock import patch

from video_tunner.post_render_verification import (
    MAX_OUTPUT_DURATION_ERROR_SECONDS,
    PASSING_POST_RENDER_JOIN_STATUSES,
    build_post_render_verification,
    rendered_join_points,
)


class PostRenderVerificationTests(unittest.TestCase):
    def test_rendered_join_points_account_for_prior_removed_time(self):
        points = rendered_join_points(
            [
                {"id": "e2", "start": 8.0, "end": 9.0, "candidate_id": "c2"},
                {"id": "e1", "start": 2.0, "end": 2.5, "candidate_id": "c1"},
            ]
        )
        self.assertEqual(points[0]["edit_id"], "e1")
        self.assertEqual(points[0]["output_join_seconds"], 2.0)
        self.assertEqual(points[1]["edit_id"], "e2")
        self.assertEqual(points[1]["output_join_seconds"], 7.5)

    def test_rendered_join_points_reject_overlaps(self):
        with self.assertRaisesRegex(ValueError, "solapados"):
            rendered_join_points(
                [
                    {"start": 2.0, "end": 3.0},
                    {"start": 2.5, "end": 4.0},
                ]
            )

    def test_duration_tolerance_is_precommitted(self):
        self.assertEqual(MAX_OUTPUT_DURATION_ERROR_SECONDS, 0.20)
        self.assertEqual(
            PASSING_POST_RENDER_JOIN_STATUSES,
            frozenset({"acoustic_context_only", "low_energy_boundary_context"}),
        )

    @patch("video_tunner.post_render_verification._measure_output_joins")
    @patch("video_tunner.post_render_verification.probe_media")
    @patch("video_tunner.post_render_verification.sha256_path")
    @patch("video_tunner.post_render_verification.Path.is_file", return_value=True)
    @patch("video_tunner.post_render_verification.validate_semantic_render_request")
    def test_clean_technical_report_still_requires_human_perceptual_gate(
        self,
        validate_chain,
        _is_file,
        sha256,
        probe,
        measure_joins,
    ):
        validate_chain.return_value = {
            "status": "valid_semantic_render_request",
            "valid": True,
        }
        sha256.side_effect = ["a" * 64, "b" * 64]
        probe.side_effect = [
            {"duration_seconds": 10.0, "video_streams": 1, "audio_streams": 1},
            {"duration_seconds": 9.6, "video_streams": 1, "audio_streams": 1},
        ]
        measure_joins.return_value = [
            {
                "id": "post-render-join-0001",
                "status": "acoustic_context_only",
                "technical_pass": True,
            }
        ]
        plan = {
            "summary": {"estimated_output_seconds": 9.6},
            "edits": [{"id": "semantic-edit-0001", "start": 2.0, "end": 2.4}],
            "plan_fingerprint": "f" * 64,
        }
        report = build_post_render_verification(
            "source.mp4",
            "output.mp4",
            {},
            {},
            {},
            plan,
            analysis_sha256="1" * 64,
            proposal_sha256="2" * 64,
            authorization_sha256="3" * 64,
        )
        self.assertEqual(report["status"], "technical_post_render_pass")
        self.assertTrue(report["technical_pass"])
        self.assertEqual(report["blockers"], [])
        self.assertFalse(report["phase2e_closeout_ready"])
        self.assertTrue(report["human_perceptual_verification"]["required"])
        self.assertFalse(report["human_perceptual_verification"]["completed"])
        self.assertFalse(report["auto_apply"])

    @patch("video_tunner.post_render_verification._measure_output_joins")
    @patch("video_tunner.post_render_verification.probe_media")
    @patch("video_tunner.post_render_verification.sha256_path")
    @patch("video_tunner.post_render_verification.Path.is_file", return_value=True)
    @patch("video_tunner.post_render_verification.validate_semantic_render_request")
    def test_duration_mismatch_fails_technical_gate(
        self,
        validate_chain,
        _is_file,
        sha256,
        probe,
        measure_joins,
    ):
        validate_chain.return_value = {"status": "valid_semantic_render_request", "valid": True}
        sha256.side_effect = ["a" * 64, "b" * 64]
        probe.side_effect = [
            {"duration_seconds": 10.0, "video_streams": 1, "audio_streams": 1},
            {"duration_seconds": 9.2, "video_streams": 1, "audio_streams": 1},
        ]
        measure_joins.return_value = []
        plan = {"summary": {"estimated_output_seconds": 9.6}, "edits": [], "plan_fingerprint": "f" * 64}
        report = build_post_render_verification(
            "source.mp4",
            "output.mp4",
            {}, {}, {}, plan,
            analysis_sha256="1" * 64,
            proposal_sha256="2" * 64,
            authorization_sha256="3" * 64,
        )
        self.assertEqual(report["status"], "technical_post_render_failed")
        self.assertFalse(report["technical_pass"])
        self.assertIn("output_duration_mismatch", {item["code"] for item in report["blockers"]})

    @patch("video_tunner.post_render_verification._measure_output_joins")
    @patch("video_tunner.post_render_verification.probe_media")
    @patch("video_tunner.post_render_verification.sha256_path")
    @patch("video_tunner.post_render_verification.Path.is_file", return_value=True)
    @patch("video_tunner.post_render_verification.validate_semantic_render_request")
    def test_post_render_join_risk_fails_technical_gate(
        self,
        validate_chain,
        _is_file,
        sha256,
        probe,
        measure_joins,
    ):
        validate_chain.return_value = {"status": "valid_semantic_render_request", "valid": True}
        sha256.side_effect = ["a" * 64, "b" * 64]
        probe.side_effect = [
            {"duration_seconds": 10.0, "video_streams": 1, "audio_streams": 1},
            {"duration_seconds": 9.6, "video_streams": 1, "audio_streams": 1},
        ]
        measure_joins.return_value = [
            {
                "id": "post-render-join-0001",
                "status": "waveform_discontinuity_risk",
                "technical_pass": False,
            }
        ]
        plan = {
            "summary": {"estimated_output_seconds": 9.6},
            "edits": [{"id": "semantic-edit-0001", "start": 2.0, "end": 2.4}],
            "plan_fingerprint": "f" * 64,
        }
        report = build_post_render_verification(
            "source.mp4", "output.mp4", {}, {}, {}, plan,
            analysis_sha256="1" * 64,
            proposal_sha256="2" * 64,
            authorization_sha256="3" * 64,
        )
        self.assertFalse(report["technical_pass"])
        self.assertIn("post_render_join_gate_failed", {item["code"] for item in report["blockers"]})

    @patch("video_tunner.post_render_verification._measure_output_joins", return_value=[])
    @patch("video_tunner.post_render_verification.probe_media")
    @patch("video_tunner.post_render_verification.sha256_path")
    @patch("video_tunner.post_render_verification.Path.is_file", return_value=True)
    @patch("video_tunner.post_render_verification.validate_semantic_render_request")
    def test_invalid_execution_chain_is_preserved_as_blocker(
        self,
        validate_chain,
        _is_file,
        sha256,
        probe,
        _measure,
    ):
        validate_chain.return_value = {
            "status": "blocked_invalid_semantic_plan",
            "valid": False,
            "reason": "plan_fingerprint_changed",
        }
        sha256.side_effect = ["a" * 64, "b" * 64]
        probe.side_effect = [
            {"duration_seconds": 10.0, "video_streams": 1, "audio_streams": 1},
            {"duration_seconds": 10.0, "video_streams": 1, "audio_streams": 1},
        ]
        report = build_post_render_verification(
            "source.mp4", "output.mp4", {}, {}, {},
            {"summary": {"estimated_output_seconds": 10.0}, "edits": []},
            analysis_sha256="1" * 64,
            proposal_sha256="2" * 64,
            authorization_sha256="3" * 64,
        )
        self.assertFalse(report["technical_pass"])
        self.assertIn("invalid_execution_chain", {item["code"] for item in report["blockers"]})


if __name__ == "__main__":
    unittest.main()
