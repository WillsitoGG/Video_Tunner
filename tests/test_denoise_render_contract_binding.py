import tempfile
import unittest
from pathlib import Path

from video_tunner.denoise_plan import build_denoise_plan_proposal
from video_tunner.denoise_render import (
    DENOISE_RENDER_AUDIO_BITRATE,
    DENOISE_RENDER_AUDIO_CODEC,
    build_denoise_remux_command,
    materialize_deepfilter_arguments,
)
from video_tunner.denoise_runtime import DEEPFILTER_ARGUMENTS, SELECTED_DENOISER_ID


NOISE_SHA = "a" * 64
SELECTION_SHA = "b" * 64
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


def ready_plan():
    return build_denoise_plan_proposal(
        noise_audit(),
        selection_review(),
        noise_audit_sha256=NOISE_SHA,
        selection_review_sha256=SELECTION_SHA,
        current_output_sha256=OUTPUT_SHA,
    )


class DenoiseRenderContractBindingTests(unittest.TestCase):
    def test_deepfilter_cli_is_materialized_exactly_from_validated_plan_template(self):
        plan = ready_plan()
        self.assertEqual(plan["runtime"]["arguments_template"], list(DEEPFILTER_ARGUMENTS))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output_dir = root / "raw"
            input_wav = root / "input.wav"
            args = materialize_deepfilter_arguments(
                plan,
                output_dir=output_dir,
                input_wav=input_wav,
            )
        self.assertEqual(args[0], "--compensate-delay")
        self.assertEqual(args[1], "--output-dir")
        self.assertEqual(args[2], str(output_dir.resolve()))
        self.assertEqual(args[3], str(input_wav.resolve()))
        self.assertNotIn("<output_dir>", args)
        self.assertNotIn("<input_wav>", args)

    def test_tampered_or_extended_deepfilter_cli_template_fails_closed(self):
        plan = ready_plan()
        tampered = {**plan, "runtime": {**plan["runtime"]}}
        tampered["runtime"]["arguments_template"] = [
            "--compensate-delay",
            "--atten-lim-db",
            "12",
            "--output-dir",
            "<output_dir>",
            "<input_wav>",
        ]
        with self.assertRaises(ValueError):
            materialize_deepfilter_arguments(
                tampered,
                output_dir="raw",
                input_wav="input.wav",
            )

    def test_remux_contract_copies_video_encodes_aac_192k_and_forbids_shortest(self):
        command = build_denoise_remux_command(
            "ffmpeg.exe",
            "source.mp4",
            "normalized.wav",
            "output.mp4",
        )
        self.assertIn("-c:v", command)
        self.assertEqual(command[command.index("-c:v") + 1], "copy")
        self.assertIn("-c:a", command)
        self.assertEqual(command[command.index("-c:a") + 1], DENOISE_RENDER_AUDIO_CODEC)
        self.assertEqual(DENOISE_RENDER_AUDIO_CODEC, "aac")
        self.assertIn("-b:a", command)
        self.assertEqual(command[command.index("-b:a") + 1], DENOISE_RENDER_AUDIO_BITRATE)
        self.assertEqual(DENOISE_RENDER_AUDIO_BITRATE, "192k")
        self.assertNotIn("-shortest", command)
        self.assertEqual(command[-1], str(Path("output.mp4").resolve()))


if __name__ == "__main__":
    unittest.main()
