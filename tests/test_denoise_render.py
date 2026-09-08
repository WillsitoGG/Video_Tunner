import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from video_tunner.denoise_execution_authorization import build_denoise_execution_authorization
from video_tunner.denoise_plan import build_denoise_plan_proposal
from video_tunner.denoise_render import (
    normalize_denoised_pcm_timeline,
    render_denoised_media,
    validate_denoise_render_request,
)
from video_tunner.denoise_runtime import DenoiserRuntimeError, SELECTED_DENOISER_ID


NOISE_SHA = "a" * 64
SELECTION_SHA = "b" * 64
PLAN_SHA = "c" * 64
AUTH_SHA = "d" * 64
QUALITY_SHA = "e" * 64
OUTPUT_SHA = "f" * 64


def noise_audit():
    return {
        "schema_version": 1,
        "record_type": "noise_evidence_audit",
        "status": "noise_measurement_complete",
        "valid": True,
        "evidence_sufficient": True,
        "quality_binding": {
            "quality_audit_sha256": QUALITY_SHA,
            "required_quality_status": "quality_audit_complete",
            "output_sha256": OUTPUT_SHA,
        },
        "window_evidence": {"speech_evidence_sha256": "1" * 64},
        "coverage": {"non_speech_window_count": 2, "non_speech_seconds": 2.5},
        "measurements": {"non_speech_energy": {"median_rms_dbfs": -42.0}},
        "interpretation": {"threshold_note": "measurement only"},
        "treatment_policy": {
            "denoise_evaluated": False,
            "denoise_authorized": False,
            "filter_selected": False,
            "parameters_defined": False,
            "normalization_authorized": False,
            "join_smoothing_authorized": False,
        },
        "executable": False,
        "treatment_authorized": False,
        "auto_apply": False,
    }


def selection_review():
    return {
        "schema_version": 1,
        "record_type": "denoiser_selection_review",
        "policy_id": "phase3_denoiser_selection_review_v1",
        "phase": "3.6f",
        "status": "SELECTED_FOR_INTEGRATION_REVIEW",
        "selection_completed": True,
        "human_eligible_candidates": [SELECTED_DENOISER_ID],
        "candidate_evaluations": [
            {
                "candidate_id": SELECTED_DENOISER_ID,
                "objective_aggregate_gate_pass": True,
                "selection_eligible": True,
            }
        ],
        "selection_eligible_candidates": [SELECTED_DENOISER_ID],
        "selected_candidate_id": SELECTED_DENOISER_ID,
        "interpretation": {
            "selected_candidate_is_for_integration_review_only": True,
            "candidate_selection_review_complete": True,
            "product_default": "preserve",
            "product_default_changed": False,
            "denoise_authorized": False,
            "renderer_authorized": False,
            "auto_apply": False,
        },
    }


def chain(*, decision="APPROVE"):
    audit = noise_audit()
    selection = selection_review()
    plan = build_denoise_plan_proposal(
        audit,
        selection,
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        current_output_sha256=OUTPUT_SHA,
    )
    authorization = build_denoise_execution_authorization(
        audit,
        selection,
        plan,
        decision=decision,
        actor="Synthetic Reviewer",
        reason="Phase 3.6i renderer contract fixture only.",
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        plan_sha256=PLAN_SHA,
        current_output_sha256=OUTPUT_SHA,
        created_utc="2026-09-08T12:30:00+00:00",
    )
    return audit, selection, plan, authorization


def runtime_validation():
    return {
        "valid": True,
        "candidate_id": SELECTED_DENOISER_ID,
        "version": "0.5.6",
        "asset_sha256": "75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915",
        "asset_size_bytes": 26912256,
        "cli_contract_pass": True,
    }


def write_wav(path: Path, frames: list[int], *, rate=48000, channels=1, width=2):
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(width)
        wav.setframerate(rate)
        if width != 2:
            wav.writeframes(b"\x00" * len(frames) * channels * width)
            return
        raw = bytearray()
        for value in frames:
            sample = int(value).to_bytes(2, "little", signed=True)
            raw.extend(sample * channels)
        wav.writeframes(bytes(raw))


def read_samples(path: Path) -> list[int]:
    with wave.open(str(path), "rb") as wav:
        raw = wav.readframes(wav.getnframes())
    return [int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)]


class DenoiseRenderTests(unittest.TestCase):
    def _validate(self, source: Path, *, decision="APPROVE", audio_channels=1):
        audit, selection, plan, authorization = chain(decision=decision)
        media = {"duration_seconds": 3.0, "video_streams": 1, "audio_streams": 1, "format_name": "mov,mp4"}
        with (
            patch("video_tunner.denoise_render.sha256_path", return_value=OUTPUT_SHA),
            patch("video_tunner.denoise_render.probe_media", return_value=media),
            patch(
                "video_tunner.denoise_render._probe_source_audio_contract",
                return_value={"channels": audio_channels, "sample_rate_hz": 48000},
            ),
            patch("video_tunner.denoise_render.validate_selected_denoiser_binary", return_value=runtime_validation()),
        ):
            return validate_denoise_render_request(
                source,
                audit,
                selection,
                plan,
                authorization,
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                plan_sha256=PLAN_SHA,
                authorization_sha256=AUTH_SHA,
            )

    def test_valid_request_requires_exact_authorized_chain_and_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"synthetic")
            result = self._validate(source)
        self.assertEqual(result["status"], "valid_denoise_render_request")
        self.assertTrue(result["valid"])
        self.assertTrue(result["render_authorized"])
        self.assertEqual(result["source_sha256"], OUTPUT_SHA)
        self.assertEqual(result["selected_candidate_id"], SELECTED_DENOISER_ID)
        self.assertTrue(result["runtime_validation"]["cli_contract_pass"])
        self.assertEqual(result["product_default"], "preserve")
        self.assertFalse(result["auto_apply"])

    def test_rejected_authorization_blocks_before_runtime(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"synthetic")
            result = self._validate(source, decision="REJECT")
        self.assertEqual(result["status"], "blocked_execution_authorization")
        self.assertFalse(result["render_authorized"])

    def test_invalid_authorization_sha_blocks_fail_closed(self):
        audit, selection, plan, authorization = chain()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"synthetic")
            result = validate_denoise_render_request(
                source,
                audit,
                selection,
                plan,
                authorization,
                noise_audit_sha256=NOISE_SHA,
                selection_review_sha256=SELECTION_SHA,
                plan_sha256=PLAN_SHA,
                authorization_sha256="bad",
            )
        self.assertEqual(result["status"], "blocked_invalid_authorization_sha")

    def test_stereo_source_is_blocked_in_initial_foundation(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"synthetic")
            result = self._validate(source, audio_channels=2)
        self.assertEqual(result["status"], "blocked_media_layout")
        self.assertEqual(result["reason"], "phase3_6i_foundation_requires_mono_source_audio")
        self.assertFalse(result["render_authorized"])

    def test_runtime_missing_or_invalid_blocks_before_render(self):
        audit, selection, plan, authorization = chain()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"synthetic")
            with (
                patch("video_tunner.denoise_render.sha256_path", return_value=OUTPUT_SHA),
                patch(
                    "video_tunner.denoise_render.probe_media",
                    return_value={"duration_seconds": 3.0, "video_streams": 1, "audio_streams": 1, "format_name": "mov,mp4"},
                ),
                patch(
                    "video_tunner.denoise_render._probe_source_audio_contract",
                    return_value={"channels": 1, "sample_rate_hz": 48000},
                ),
                patch(
                    "video_tunner.denoise_render.validate_selected_denoiser_binary",
                    side_effect=DenoiserRuntimeError("missing exact portable binary"),
                ),
            ):
                result = validate_denoise_render_request(
                    source,
                    audit,
                    selection,
                    plan,
                    authorization,
                    noise_audit_sha256=NOISE_SHA,
                    selection_review_sha256=SELECTION_SHA,
                    plan_sha256=PLAN_SHA,
                    authorization_sha256=AUTH_SHA,
                )
        self.assertEqual(result["status"], "blocked_runtime_contract")
        self.assertFalse(result["render_authorized"])

    def test_source_overwrite_is_forbidden_before_gate_execution(self):
        audit, selection, plan, authorization = chain()
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source.mp4"
            source.write_bytes(b"synthetic")
            with self.assertRaises(ValueError):
                render_denoised_media(
                    source,
                    audit,
                    selection,
                    plan,
                    authorization,
                    source,
                    noise_audit_sha256=NOISE_SHA,
                    selection_review_sha256=SELECTION_SHA,
                    plan_sha256=PLAN_SHA,
                    authorization_sha256=AUTH_SHA,
                )

    def test_tail_trim_preserves_prefix_and_exact_input_length(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.wav"
            candidate = root / "candidate.wav"
            output = root / "output.wav"
            input_samples = list(range(1000))
            candidate_samples = list(range(1010))
            write_wav(source, input_samples)
            write_wav(candidate, candidate_samples)
            result = normalize_denoised_pcm_timeline(source, candidate, output)
            self.assertEqual(result["timeline_normalization_action"], "trim_right_tail")
            self.assertEqual(result["raw_frame_delta"], 10)
            self.assertEqual(result["final_frames"], 1000)
            self.assertEqual(read_samples(output), candidate_samples[:1000])
            self.assertFalse(result["alignment_search_performed"])
            self.assertFalse(result["time_shift_performed"])
            self.assertFalse(result["level_matching_performed"])

    def test_tail_pad_appends_only_digital_silence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.wav"
            candidate = root / "candidate.wav"
            output = root / "output.wav"
            write_wav(source, list(range(1000)))
            candidate_samples = list(range(990))
            write_wav(candidate, candidate_samples)
            result = normalize_denoised_pcm_timeline(source, candidate, output)
            rendered = read_samples(output)
            self.assertEqual(result["timeline_normalization_action"], "pad_right_tail_silence")
            self.assertEqual(rendered[:990], candidate_samples)
            self.assertEqual(rendered[990:], [0] * 10)

    def test_equal_length_timeline_is_not_mutated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.wav"
            candidate = root / "candidate.wav"
            output = root / "output.wav"
            samples = list(range(1000))
            write_wav(source, samples)
            write_wav(candidate, samples)
            result = normalize_denoised_pcm_timeline(source, candidate, output)
            self.assertEqual(result["timeline_normalization_action"], "none")
            self.assertEqual(read_samples(output), samples)

    def test_raw_duration_delta_above_frozen_limit_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "input.wav"
            candidate = root / "candidate.wav"
            output = root / "output.wav"
            write_wav(source, [1] * 1000)
            write_wav(candidate, [1] * (1000 + 2401))
            with self.assertRaises(ValueError):
                normalize_denoised_pcm_timeline(source, candidate, output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
