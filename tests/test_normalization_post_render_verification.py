import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.normalization_post_render_verification import (
    DURATION_TOLERANCE_SECONDS,
    PROGRAMME_LOUDNESS_TOLERANCE_LU,
    build_normalization_post_render_verification,
)


SOURCE_SHA = "a" * 64
OUTPUT_SHA = "b" * 64
QUALITY_SHA = "c" * 64
PROFILE_SHA = "d" * 64
APPROVAL_SHA = "e" * 64
PLAN_SHA = "1" * 64
AUTH_SHA = "2" * 64
RENDER_SHA = "3" * 64
VIDEO_SHA = "4" * 64


def plan():
    return {
        "targets": {"target_i": -23.0, "target_tp": -1.0},
    }


def render_result():
    source_media = {
        "file": "source.mp4",
        "duration_seconds": 12.0,
        "video_streams": 1,
        "audio_streams": 1,
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
    }
    output_media = dict(source_media)
    output_media["file"] = "output.mp4"
    return {
        "schema_version": 1,
        "record_type": "normalization_render_result",
        "status": "normalization_render_complete",
        "source": {"file": "source.mp4", "sha256": SOURCE_SHA, "media": source_media},
        "output": {"file": "output.mp4", "sha256": OUTPUT_SHA, "media": output_media},
        "bindings": {
            "quality_audit_sha256": QUALITY_SHA,
            "profile_decision_sha256": PROFILE_SHA,
            "approval_sha256": APPROVAL_SHA,
            "plan_sha256": PLAN_SHA,
            "authorization_sha256": AUTH_SHA,
            "profile_name": "ebu_r128_programme",
        },
        "ffmpeg_loudnorm": {
            "input_i": -30.0,
            "input_tp": -10.0,
            "input_lra": 8.5,
            "input_thresh": -40.0,
            "output_i": -23.0,
            "output_tp": -3.0,
            "output_lra": 8.5,
            "output_thresh": -33.0,
            "target_offset": 0.0,
            "normalization_type": "linear",
        },
        "video_policy": "stream_copy_first_and_only_video_stream",
        "audio_policy": "aac_192k_first_and_only_audio_stream_after_authorized_linear_loudnorm",
        "technical_post_render_verification_required": True,
        "human_perceptual_review_required": True,
        "technical_pass": False,
        "human_pass": False,
        "auto_apply": False,
    }


def valid_request():
    return {
        "status": "valid_normalization_render_request",
        "valid": True,
        "render_authorized": True,
        "source_sha256": SOURCE_SHA,
        "profile_name": "ebu_r128_programme",
        "auto_apply": False,
    }


def media(path: Path):
    return {
        "file": path.name,
        "duration_seconds": 12.0,
        "video_streams": 1,
        "audio_streams": 1,
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
    }


def build(source: Path, output: Path, result: dict):
    return build_normalization_post_render_verification(
        source,
        output,
        {},
        {},
        {},
        plan(),
        {},
        result,
        quality_audit_sha256=QUALITY_SHA,
        profile_decision_sha256=PROFILE_SHA,
        approval_sha256=APPROVAL_SHA,
        plan_sha256=PLAN_SHA,
        authorization_sha256=AUTH_SHA,
        render_result_sha256=RENDER_SHA,
    )


class NormalizationPostRenderVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mp4"
        self.output = self.root / "output.mp4"
        self.source.write_bytes(b"source")
        self.output.write_bytes(b"output")

    def tearDown(self):
        self.temp.cleanup()

    def _patches(self, *, audio_i=-23.0, audio_tp=-3.0, source_video=VIDEO_SHA, output_video=VIDEO_SHA, output_duration=12.0):
        source_media = media(self.source)
        output_media = media(self.output)
        output_media["duration_seconds"] = output_duration
        result = render_result()
        result["source"]["media"] = source_media
        result["output"]["media"] = output_media
        return result, (
            patch("video_tunner.normalization_post_render_verification.validate_normalization_render_request", return_value=valid_request()),
            patch("video_tunner.normalization_post_render_verification.sha256_path", side_effect=[SOURCE_SHA, OUTPUT_SHA]),
            patch("video_tunner.normalization_post_render_verification.probe_media", side_effect=[source_media, output_media]),
            patch("video_tunner.normalization_post_render_verification.decoded_video_sha256", side_effect=[source_video, output_video]),
            patch(
                "video_tunner.normalization_post_render_verification.measure_audio_loudness",
                return_value={
                    "integrated_lufs": audio_i,
                    "true_peak_dbtp": audio_tp,
                    "loudness_range_lu": 8.5,
                    "threshold_lufs": -33.0,
                },
            ),
        )

    def _run_with_patches(self, **kwargs):
        result, patches = self._patches(**kwargs)
        entered = [p.start() for p in patches]
        try:
            return build(self.source, self.output, result)
        finally:
            for p in reversed(patches):
                p.stop()

    def test_valid_output_passes_technical_gate_but_not_human_gate(self):
        verification = self._run_with_patches()
        self.assertEqual(verification["status"], "technical_normalization_pass")
        self.assertTrue(verification["valid_evidence"])
        self.assertTrue(verification["technical_pass"])
        self.assertTrue(verification["human_perceptual_review_required"])
        self.assertFalse(verification["human_pass"])
        self.assertEqual(verification["blockers"], [])
        self.assertEqual(verification["targets"]["programme_loudness_tolerance_lu"], PROGRAMME_LOUDNESS_TOLERANCE_LU)
        self.assertEqual(verification["targets"]["duration_tolerance_seconds"], DURATION_TOLERANCE_SECONDS)
        self.assertFalse(verification["auto_apply"])

    def test_changed_output_sha_is_invalid_evidence_not_quality_fail(self):
        result, patches = self._patches()
        result["output"]["sha256"] = "9" * 64
        for p in patches:
            p.start()
        try:
            verification = build(self.source, self.output, result)
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertEqual(verification["status"], "invalid_evidence")
        self.assertFalse(verification["valid_evidence"])
        self.assertFalse(verification["technical_pass"])

    def test_independent_loudness_outside_half_lu_fails_quality(self):
        verification = self._run_with_patches(audio_i=-22.49)
        self.assertEqual(verification["status"], "technical_normalization_fail")
        self.assertTrue(verification["valid_evidence"])
        self.assertIn("programme_loudness_out_of_tolerance", [b["code"] for b in verification["blockers"]])

    def test_true_peak_above_profile_maximum_fails_quality_without_relaxation(self):
        verification = self._run_with_patches(audio_tp=-0.99)
        self.assertEqual(verification["status"], "technical_normalization_fail")
        self.assertIn("true_peak_limit_exceeded", [b["code"] for b in verification["blockers"]])

    def test_decoded_video_change_fails_quality(self):
        verification = self._run_with_patches(output_video="5" * 64)
        self.assertEqual(verification["status"], "technical_normalization_fail")
        self.assertIn("decoded_video_changed_during_audio_normalization", [b["code"] for b in verification["blockers"]])

    def test_duration_delta_above_precommitted_tolerance_fails_quality(self):
        verification = self._run_with_patches(output_duration=12.151)
        self.assertEqual(verification["status"], "technical_normalization_fail")
        self.assertIn("duration_delta_exceeded", [b["code"] for b in verification["blockers"]])

    def test_non_linear_render_result_is_invalid_evidence(self):
        result, patches = self._patches()
        result["ffmpeg_loudnorm"]["normalization_type"] = "dynamic"
        for p in patches:
            p.start()
        try:
            verification = build(self.source, self.output, result)
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertEqual(verification["status"], "invalid_evidence")
        self.assertFalse(verification["technical_pass"])

    def test_premature_pass_claim_in_render_result_is_invalid_evidence(self):
        result, patches = self._patches()
        result["technical_pass"] = True
        for p in patches:
            p.start()
        try:
            verification = build(self.source, self.output, result)
        finally:
            for p in reversed(patches):
                p.stop()
        self.assertEqual(verification["status"], "invalid_evidence")
        self.assertFalse(verification["technical_pass"])


if __name__ == "__main__":
    unittest.main()
