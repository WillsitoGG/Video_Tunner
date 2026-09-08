import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.denoise_post_render_verification import build_denoise_post_render_verification


SOURCE_SHA = "1" * 64
OUTPUT_SHA = "2" * 64
NOISE_SHA = "3" * 64
SELECTION_SHA = "4" * 64
PLAN_SHA = "5" * 64
AUTH_SHA = "6" * 64
RENDER_SHA = "7" * 64
RUNTIME_FP = "8" * 64
CANDIDATE_ID = "deepfilternet_0_5_6_compensated_v1"


class DenoisePostRenderVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="video_tunner_denoise_verify_test_")
        self.root = Path(self.temp.name)
        self.source = self.root / "source.mp4"
        self.output = self.root / "output.mp4"
        self.source.write_bytes(b"source")
        self.output.write_bytes(b"output")
        self.source_media = {
            "file": self.source.name,
            "duration_seconds": 3.0,
            "video_streams": 1,
            "audio_streams": 1,
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        }
        self.output_media = {
            "file": self.output.name,
            "duration_seconds": 3.0,
            "video_streams": 1,
            "audio_streams": 1,
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        }
        self.source_audio = {"channels": 1, "sample_rate_hz": 48000}
        self.runtime = {
            "valid": True,
            "candidate_id": CANDIDATE_ID,
            "version": "0.5.6",
            "asset_sha256": "9" * 64,
            "asset_size_bytes": 26912256,
            "cli_contract_pass": True,
        }
        self.request = {
            "status": "valid_denoise_render_request",
            "valid": True,
            "render_authorized": True,
            "source_sha256": SOURCE_SHA,
            "source_media": self.source_media,
            "source_audio": self.source_audio,
            "authorization_sha256": AUTH_SHA,
            "selected_candidate_id": CANDIDATE_ID,
            "runtime_contract_fingerprint": RUNTIME_FP,
            "runtime_validation": self.runtime,
            "product_default": "preserve",
            "auto_apply": False,
        }
        self.timeline = {
            "input_frames": 144000,
            "raw_output_frames": 142560,
            "raw_frame_delta": -1440,
            "raw_duration_delta_seconds": -0.03,
            "max_abs_raw_duration_delta_seconds": 0.05,
            "timeline_normalization_action": "pad_right_tail_silence",
            "final_frames": 144000,
            "alignment_search_performed": False,
            "time_shift_performed": False,
            "level_matching_performed": False,
        }
        self.render_result = {
            "schema_version": 1,
            "record_type": "denoise_render_result",
            "status": "denoise_render_complete",
            "source": {
                "file": self.source.name,
                "sha256": SOURCE_SHA,
                "media": self.source_media,
                "audio": self.source_audio,
            },
            "output": {
                "file": self.output.name,
                "sha256": OUTPUT_SHA,
                "media": self.output_media,
            },
            "bindings": {
                "noise_audit_sha256": NOISE_SHA,
                "selection_review_sha256": SELECTION_SHA,
                "plan_sha256": PLAN_SHA,
                "authorization_sha256": AUTH_SHA,
                "selected_candidate_id": CANDIDATE_ID,
                "runtime_contract_fingerprint": RUNTIME_FP,
            },
            "runtime": self.runtime,
            "timeline": self.timeline,
            "video_policy": "stream_copy_first_and_only_video_stream",
            "audio_policy": "deepfilternet_compensated_pcm16_mono_48k_then_aac_192k",
            "source_overwritten": False,
            "technical_post_render_verification_required": True,
            "human_perceptual_review_required": True,
            "technical_pass": False,
            "human_pass": False,
            "product_default": "preserve",
            "auto_apply": False,
        }

    def tearDown(self):
        self.temp.cleanup()

    def _build(self, render_result=None):
        if render_result is None:
            render_result = self.render_result
        with (
            patch(
                "video_tunner.denoise_post_render_verification.validate_denoise_render_request",
                return_value=self.request,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.sha256_path",
                side_effect=lambda path: SOURCE_SHA if Path(path).resolve() == self.source.resolve() else OUTPUT_SHA,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.probe_media",
                side_effect=lambda path: self.source_media
                if Path(path).resolve() == self.source.resolve()
                else self.output_media,
            ),
            patch(
                "video_tunner.denoise_post_render_verification._probe_audio_stream_contract",
                return_value={"codec_name": "aac", "channels": 1, "sample_rate_hz": 48000},
            ),
            patch(
                "video_tunner.denoise_post_render_verification.decoded_video_sha256",
                return_value="a" * 64,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.decoded_audio_frame_count_48k_mono",
                return_value=144000,
            ),
        ):
            return build_denoise_post_render_verification(
                self.source,
                self.output,
                {},
                {},
                {},
                {},
                render_result,
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                plan_sha256=PLAN_SHA,
                authorization_sha256=AUTH_SHA,
                render_result_sha256=RENDER_SHA,
            )

    def test_valid_current_render_passes_technical_gate_but_not_human_gate(self):
        record = self._build()
        self.assertEqual(record["status"], "technical_denoise_pass")
        self.assertTrue(record["valid_evidence"])
        self.assertTrue(record["technical_pass"])
        self.assertTrue(record["human_perceptual_review_required"])
        self.assertFalse(record["human_pass"])
        self.assertEqual(record["blockers"], [])
        self.assertEqual(record["product_default"], "preserve")
        self.assertFalse(record["auto_apply"])
        self.assertFalse(record["technical_policy"]["objective_or_perceptual_thresholds_added"])

    def test_premature_pass_claim_in_render_result_is_invalid_evidence(self):
        tampered = dict(self.render_result)
        tampered["technical_pass"] = True
        record = self._build(tampered)
        self.assertEqual(record["status"], "invalid_evidence")
        self.assertFalse(record["valid_evidence"])
        self.assertEqual(record["blockers"][0]["code"], "render_result_contains_premature_pass_or_auto_apply")

    def test_changed_binding_is_invalid_evidence(self):
        tampered = dict(self.render_result)
        tampered["bindings"] = dict(self.render_result["bindings"])
        tampered["bindings"]["authorization_sha256"] = "0" * 64
        record = self._build(tampered)
        self.assertEqual(record["status"], "invalid_evidence")
        self.assertEqual(record["blockers"][0]["code"], "render_result_bindings_changed")

    def test_internally_inconsistent_reported_timeline_is_invalid_evidence(self):
        tampered = dict(self.render_result)
        tampered["timeline"] = dict(self.timeline)
        tampered["timeline"]["raw_frame_delta"] = -1000
        record = self._build(tampered)
        self.assertEqual(record["status"], "invalid_evidence")
        self.assertEqual(
            record["blockers"][0]["code"],
            "render_result_timeline_raw_frame_delta_inconsistent",
        )

    def test_stale_upstream_chain_is_invalid_evidence(self):
        blocked = {"status": "blocked_source_mismatch", "reason": "quality_output_sha256_changed"}
        with patch(
            "video_tunner.denoise_post_render_verification.validate_denoise_render_request",
            return_value=blocked,
        ):
            record = build_denoise_post_render_verification(
                self.source,
                self.output,
                {},
                {},
                {},
                {},
                self.render_result,
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                plan_sha256=PLAN_SHA,
                authorization_sha256=AUTH_SHA,
                render_result_sha256=RENDER_SHA,
            )
        self.assertEqual(record["status"], "invalid_evidence")
        self.assertEqual(record["blockers"][0]["code"], "stale_or_invalid_denoise_chain")

    def test_decoded_video_change_is_technical_fail_not_invalid_evidence(self):
        with (
            patch(
                "video_tunner.denoise_post_render_verification.validate_denoise_render_request",
                return_value=self.request,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.sha256_path",
                side_effect=lambda path: SOURCE_SHA if Path(path).resolve() == self.source.resolve() else OUTPUT_SHA,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.probe_media",
                side_effect=lambda path: self.source_media
                if Path(path).resolve() == self.source.resolve()
                else self.output_media,
            ),
            patch(
                "video_tunner.denoise_post_render_verification._probe_audio_stream_contract",
                return_value={"codec_name": "aac", "channels": 1, "sample_rate_hz": 48000},
            ),
            patch(
                "video_tunner.denoise_post_render_verification.decoded_video_sha256",
                side_effect=["a" * 64, "b" * 64],
            ),
            patch(
                "video_tunner.denoise_post_render_verification.decoded_audio_frame_count_48k_mono",
                return_value=144000,
            ),
        ):
            record = build_denoise_post_render_verification(
                self.source,
                self.output,
                {},
                {},
                {},
                {},
                self.render_result,
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                plan_sha256=PLAN_SHA,
                authorization_sha256=AUTH_SHA,
                render_result_sha256=RENDER_SHA,
            )
        self.assertTrue(record["valid_evidence"])
        self.assertFalse(record["technical_pass"])
        self.assertEqual(record["status"], "technical_denoise_fail")
        self.assertIn("decoded_video_changed_during_denoise", [item["code"] for item in record["blockers"]])

    def test_output_audio_codec_change_is_technical_fail(self):
        with patch(
            "video_tunner.denoise_post_render_verification._probe_audio_stream_contract",
            return_value={"codec_name": "opus", "channels": 1, "sample_rate_hz": 48000},
        ):
            with (
                patch(
                    "video_tunner.denoise_post_render_verification.validate_denoise_render_request",
                    return_value=self.request,
                ),
                patch(
                    "video_tunner.denoise_post_render_verification.sha256_path",
                    side_effect=lambda path: SOURCE_SHA if Path(path).resolve() == self.source.resolve() else OUTPUT_SHA,
                ),
                patch(
                    "video_tunner.denoise_post_render_verification.probe_media",
                    side_effect=lambda path: self.source_media
                    if Path(path).resolve() == self.source.resolve()
                    else self.output_media,
                ),
                patch(
                    "video_tunner.denoise_post_render_verification.decoded_video_sha256",
                    return_value="a" * 64,
                ),
                patch(
                    "video_tunner.denoise_post_render_verification.decoded_audio_frame_count_48k_mono",
                    return_value=144000,
                ),
            ):
                record = build_denoise_post_render_verification(
                    self.source,
                    self.output,
                    {},
                    {},
                    {},
                    {},
                    self.render_result,
                    noise_audit_sha256=NOISE_SHA,
                    selection_review_sha256=SELECTION_SHA,
                    plan_sha256=PLAN_SHA,
                    authorization_sha256=AUTH_SHA,
                    render_result_sha256=RENDER_SHA,
                )
        self.assertTrue(record["valid_evidence"])
        self.assertFalse(record["technical_pass"])
        self.assertIn("output_audio_codec_changed", [item["code"] for item in record["blockers"]])

    def test_independent_audio_frame_mismatch_is_technical_fail(self):
        with (
            patch(
                "video_tunner.denoise_post_render_verification.validate_denoise_render_request",
                return_value=self.request,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.sha256_path",
                side_effect=lambda path: SOURCE_SHA if Path(path).resolve() == self.source.resolve() else OUTPUT_SHA,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.probe_media",
                side_effect=lambda path: self.source_media
                if Path(path).resolve() == self.source.resolve()
                else self.output_media,
            ),
            patch(
                "video_tunner.denoise_post_render_verification._probe_audio_stream_contract",
                return_value={"codec_name": "aac", "channels": 1, "sample_rate_hz": 48000},
            ),
            patch(
                "video_tunner.denoise_post_render_verification.decoded_video_sha256",
                return_value="a" * 64,
            ),
            patch(
                "video_tunner.denoise_post_render_verification.decoded_audio_frame_count_48k_mono",
                side_effect=[144000, 143999],
            ),
        ):
            record = build_denoise_post_render_verification(
                self.source,
                self.output,
                {},
                {},
                {},
                {},
                self.render_result,
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                plan_sha256=PLAN_SHA,
                authorization_sha256=AUTH_SHA,
                render_result_sha256=RENDER_SHA,
            )
        codes = [item["code"] for item in record["blockers"]]
        self.assertTrue(record["valid_evidence"])
        self.assertFalse(record["technical_pass"])
        self.assertIn("independent_output_audio_frames_mismatch", codes)
        self.assertIn("independent_decoded_audio_timeline_changed", codes)

    def test_changed_output_sha_snapshot_is_invalid_evidence(self):
        tampered = dict(self.render_result)
        tampered["output"] = dict(self.render_result["output"])
        tampered["output"]["sha256"] = "0" * 64
        record = self._build(tampered)
        self.assertEqual(record["status"], "invalid_evidence")
        self.assertEqual(record["blockers"][0]["code"], "render_result_output_sha_changed")


if __name__ == "__main__":
    unittest.main()
