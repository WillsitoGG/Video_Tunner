import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.normalization_approval import build_normalization_approval
from video_tunner.normalization_execution_authorization import build_normalization_execution_authorization
from video_tunner.normalization_plan import build_normalization_plan_proposal
from video_tunner.normalization_render import (
    build_linear_loudnorm_filter,
    parse_loudnorm_render_summary,
    render_normalized_media,
    validate_normalization_render_request,
)


QUALITY_SHA = "c" * 64
PROFILE_SHA = "d" * 64
APPROVAL_SHA = "e" * 64
PLAN_SHA = "1" * 64
AUTH_SHA = "2" * 64
OUTPUT_SHA = "a" * 64


def quality_audit():
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
                "integrated_lufs": -30.0,
                "true_peak_dbtp": -10.0,
                "loudness_range_lu": 8.5,
                "threshold_lufs": -40.0,
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


def chain(*, execution_decision="APPROVE"):
    quality = quality_audit()
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
    authorization = build_normalization_execution_authorization(
        quality,
        profile,
        approval,
        plan,
        decision=execution_decision,
        actor="Guille",
        reason="Authorize only gated linear normalization.",
        quality_audit_sha256=QUALITY_SHA,
        profile_decision_sha256=PROFILE_SHA,
        approval_sha256=APPROVAL_SHA,
        plan_sha256=PLAN_SHA,
        created_utc="2026-09-07T15:20:00+00:00",
    )
    return quality, profile, approval, plan, authorization


def validate(source, quality, profile, approval, plan, authorization):
    return validate_normalization_render_request(
        source,
        quality,
        profile,
        approval,
        plan,
        authorization,
        quality_audit_sha256=QUALITY_SHA,
        profile_decision_sha256=PROFILE_SHA,
        approval_sha256=APPROVAL_SHA,
        plan_sha256=PLAN_SHA,
        authorization_sha256=AUTH_SHA,
    )


class NormalizationRenderTests(unittest.TestCase):
    def test_loudnorm_summary_parser_requires_and_returns_linear_type(self):
        stderr = '''noise\n{
          "input_i" : "-30.00", "input_tp" : "-10.00", "input_lra" : "8.50", "input_thresh" : "-40.00",
          "output_i" : "-23.00", "output_tp" : "-3.00", "output_lra" : "8.50", "output_thresh" : "-33.00",
          "normalization_type" : "linear", "target_offset" : "0.00"
        }\n'''
        parsed = parse_loudnorm_render_summary(stderr)
        self.assertEqual(parsed["normalization_type"], "linear")
        self.assertEqual(parsed["output_i"], -23.0)
        self.assertEqual(parsed["target_offset"], 0.0)

    def test_filter_is_explicit_linear_two_pass_without_offset_parameter(self):
        _, _, _, plan, _ = chain()
        spec = build_linear_loudnorm_filter(plan)
        self.assertIn("linear=true", spec)
        self.assertIn("measured_I=-30.000000", spec)
        self.assertIn("measured_TP=-10.000000", spec)
        self.assertIn("measured_LRA=8.500000", spec)
        self.assertIn("measured_thresh=-40.000000", spec)
        self.assertNotIn(":offset=", spec)

    def test_rejected_execution_authorization_blocks_before_ffmpeg(self):
        quality, profile, approval, plan, authorization = chain(execution_decision="REJECT")
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            source.write_bytes(b"x")
            with patch("video_tunner.normalization_render.sha256_path", return_value=OUTPUT_SHA):
                result = validate(source, quality, profile, approval, plan, authorization)
        self.assertEqual(result["status"], "blocked_execution_authorization")
        self.assertFalse(result["render_authorized"])

    def test_source_sha_mismatch_blocks_before_media_probe(self):
        quality, profile, approval, plan, authorization = chain()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            source.write_bytes(b"x")
            with patch("video_tunner.normalization_render.sha256_path", return_value="9" * 64), patch(
                "video_tunner.normalization_render.probe_media"
            ) as probe:
                result = validate(source, quality, profile, approval, plan, authorization)
                probe.assert_not_called()
        self.assertEqual(result["status"], "blocked_source_mismatch")
        self.assertFalse(result["render_authorized"])

    def test_media_layout_requires_exactly_one_video_and_audio_stream(self):
        quality, profile, approval, plan, authorization = chain()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            source.write_bytes(b"x")
            with patch("video_tunner.normalization_render.sha256_path", return_value=OUTPUT_SHA), patch(
                "video_tunner.normalization_render.probe_media",
                return_value={"video_streams": 1, "audio_streams": 2, "duration_seconds": 10.0},
            ):
                result = validate(source, quality, profile, approval, plan, authorization)
        self.assertEqual(result["status"], "blocked_media_layout")
        self.assertFalse(result["render_authorized"])

    def test_tampered_plan_dynamic_fallback_is_rejected_upstream(self):
        quality, profile, approval, plan, authorization = chain()
        tampered = copy.deepcopy(plan)
        tampered["policy"]["dynamic_fallback_allowed"] = True
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            source.write_bytes(b"x")
            with patch("video_tunner.normalization_render.sha256_path", return_value=OUTPUT_SHA):
                result = validate(source, quality, profile, approval, tampered, authorization)
        self.assertEqual(result["status"], "blocked_execution_authorization")
        self.assertFalse(result["render_authorized"])

    def test_renderer_never_overwrites_source(self):
        quality, profile, approval, plan, authorization = chain()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source.mp4"
            source.write_bytes(b"x")
            with self.assertRaises(ValueError):
                render_normalized_media(
                    source,
                    quality,
                    profile,
                    approval,
                    plan,
                    authorization,
                    source,
                    quality_audit_sha256=QUALITY_SHA,
                    profile_decision_sha256=PROFILE_SHA,
                    approval_sha256=APPROVAL_SHA,
                    plan_sha256=PLAN_SHA,
                    authorization_sha256=AUTH_SHA,
                )


if __name__ == "__main__":
    unittest.main()
