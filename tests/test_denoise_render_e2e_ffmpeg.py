import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_tunner.approval import sha256_path
from video_tunner.denoise_execution_authorization import build_denoise_execution_authorization
from video_tunner.denoise_plan import build_denoise_plan_proposal
from video_tunner.denoise_render import render_denoised_media
from video_tunner.denoise_runtime import SELECTED_DENOISER_ID, deepfilter_executable_path
from video_tunner.tools import resolve_tool


QUALITY_SHA = "9" * 64


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


def noise_audit(output_sha: str):
    return {
        "schema_version": 1,
        "record_type": "noise_evidence_audit",
        "status": "noise_measurement_complete",
        "valid": True,
        "evidence_sufficient": True,
        "quality_binding": {
            "quality_audit_sha256": QUALITY_SHA,
            "required_quality_status": "quality_audit_complete",
            "output_sha256": output_sha,
        },
        "window_evidence": {"speech_evidence_sha256": "8" * 64},
        "coverage": {"non_speech_window_count": 2, "non_speech_seconds": 2.5},
        "measurements": {"non_speech_energy": {"median_rms_dbfs": -42.0}},
        "interpretation": {
            "metric_scope": "synthetic renderer fixture",
            "threshold_note": "No measured dBFS value is a denoise threshold.",
        },
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


def write_json(path: Path, payload: dict) -> str:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return sha256_path(path)


def run_checked(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(command)}\n{completed.stderr}")


class DenoiseRenderEndToEndTests(unittest.TestCase):
    @unittest.skipUnless(deepfilter_executable_path().is_file(), "Exact DeepFilterNet runtime not staged")
    def test_full_synthetic_authorized_chain_renders_real_deepfilternet_without_declaring_pass(self):
        ffmpeg = resolve_tool("ffmpeg")
        with tempfile.TemporaryDirectory(prefix="video_tunner_denoise_e2e_") as temporary:
            root = Path(temporary)
            source = root / "synthetic_source.mp4"
            output = root / "synthetic_denoised.mp4"

            run_checked(
                [
                    str(ffmpeg),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "color=c=black:s=320x240:r=25:d=3",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=3",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "mpeg4",
                    "-q:v",
                    "5",
                    "-c:a",
                    "aac",
                    "-ac",
                    "1",
                    "-shortest",
                    str(source),
                ]
            )
            source_sha_before = sha256_path(source)

            audit = noise_audit(source_sha_before)
            selection = selection_review()
            noise_sha = write_json(root / "noise_audit.json", audit)
            selection_sha = write_json(root / "selection_review.json", selection)
            plan = build_denoise_plan_proposal(
                audit,
                selection,
                noise_audit_sha256=noise_sha,
                selection_review_sha256=selection_sha,
                current_output_sha256=source_sha_before,
            )
            plan_sha = write_json(root / "denoise_plan.json", plan)
            authorization = build_denoise_execution_authorization(
                audit,
                selection,
                plan,
                decision="APPROVE",
                actor="Synthetic Reviewer",
                reason="Phase 3.6i real-tool E2E fixture only; not user-media authorization.",
                noise_audit_sha256=noise_sha,
                selection_review_sha256=selection_sha,
                plan_sha256=plan_sha,
                current_output_sha256=source_sha_before,
                created_utc="2026-09-08T12:45:00+00:00",
            )
            authorization_sha = write_json(root / "denoise_authorization.json", authorization)

            result = render_denoised_media(
                source,
                audit,
                selection,
                plan,
                authorization,
                output,
                noise_audit_sha256=noise_sha,
                selection_review_sha256=selection_sha,
                plan_sha256=plan_sha,
                authorization_sha256=authorization_sha,
            )

            self.assertTrue(output.is_file())
            self.assertEqual(sha256_path(source), source_sha_before)
            self.assertEqual(result["status"], "denoise_render_complete")
            self.assertEqual(result["source"]["sha256"], source_sha_before)
            self.assertEqual(result["bindings"]["selected_candidate_id"], SELECTED_DENOISER_ID)
            self.assertEqual(result["source"]["audio"]["channels"], 1)
            self.assertEqual(result["output"]["media"]["video_streams"], 1)
            self.assertEqual(result["output"]["media"]["audio_streams"], 1)
            self.assertLessEqual(abs(result["timeline"]["raw_duration_delta_seconds"]), 0.05)
            self.assertEqual(result["timeline"]["final_frames"], result["timeline"]["input_frames"])
            self.assertFalse(result["timeline"]["alignment_search_performed"])
            self.assertFalse(result["timeline"]["time_shift_performed"])
            self.assertFalse(result["timeline"]["level_matching_performed"])
            self.assertTrue(result["technical_post_render_verification_required"])
            self.assertTrue(result["human_perceptual_review_required"])
            self.assertFalse(result["technical_pass"])
            self.assertFalse(result["human_pass"])
            self.assertEqual(result["product_default"], "preserve")
            self.assertFalse(result["auto_apply"])


if __name__ == "__main__":
    unittest.main()
