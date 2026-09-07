import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_tunner.approval import sha256_path
from video_tunner.audiovisual_quality import measure_audio_loudness
from video_tunner.audiovisual_treatment import build_audiovisual_treatment_decision
from video_tunner.normalization_approval import build_normalization_approval
from video_tunner.normalization_execution_authorization import build_normalization_execution_authorization
from video_tunner.normalization_plan import build_normalization_plan_proposal
from video_tunner.normalization_post_render_verification import build_normalization_post_render_verification
from video_tunner.normalization_profiles import build_normalization_profile_decision
from video_tunner.normalization_render import render_normalized_media
from video_tunner.tools import ToolNotFoundError, resolve_tool


class NormalizationRenderEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = resolve_tool("ffmpeg")
        except ToolNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def _make_variable_level_media(self, path: Path) -> None:
        completed = subprocess.run(
            [
                str(self.ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=black:s=320x240:r=25:d=12",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=6",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=6",
                "-filter_complex",
                "[1:a]volume=0.08[a1];[2:a]volume=0.40[a2];[a1][a2]concat=n=2:v=0:a=1[a]",
                "-map",
                "0:v:0",
                "-map",
                "[a]",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-movflags",
                "+faststart",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            self.fail(completed.stderr)

    @staticmethod
    def _write_json(path: Path, payload: dict) -> str:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return sha256_path(path)

    def test_full_authorized_chain_renders_and_technically_verifies_linear_ebu_profile(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "phase2e_output.mp4"
            output = root / "normalized.mp4"
            self._make_variable_level_media(source)
            source_sha_before = sha256_path(source)
            measured = measure_audio_loudness(source)

            self.assertGreaterEqual(measured["loudness_range_lu"], 1.0)
            self.assertNotEqual(measured["integrated_lufs"], 0.0)
            self.assertNotEqual(measured["threshold_lufs"], -70.0)

            quality = {
                "schema_version": 1,
                "record_type": "audiovisual_quality_audit",
                "status": "quality_audit_complete",
                "valid": True,
                "phase2e_binding": {
                    "required_status": "technical_post_render_pass",
                    "technical_report_sha256": "b" * 64,
                    "source_sha256": "f" * 64,
                    "output_sha256": source_sha_before,
                    "join_count": 1,
                },
                "measurements": {
                    "source_audio": measured,
                    "output_audio": measured,
                    "delta": {
                        "integrated_loudness_delta_lu": 0.0,
                        "true_peak_delta_db": 0.0,
                    },
                },
                "findings": [],
                "summary": {
                    "finding_count": 0,
                    "risk_count": 0,
                    "quality_review_required": False,
                },
                "treatment_policy": {
                    "normalization_evaluated": False,
                    "normalization_authorized": False,
                    "denoise_evaluated": False,
                    "denoise_authorized": False,
                    "join_smoothing_evaluated": False,
                    "join_smoothing_authorized": False,
                },
                "treatment_authorized": False,
                "auto_apply": False,
            }
            quality_sha = self._write_json(root / "quality.json", quality)

            treatment = build_audiovisual_treatment_decision(quality)
            profile = build_normalization_profile_decision(
                treatment,
                profile_name="ebu_r128_programme",
            )
            profile_sha = self._write_json(root / "profile.json", profile)

            approval = build_normalization_approval(
                profile,
                decision="APPROVE",
                actor="Guille",
                reason="E2E explicit standards-profile approval.",
                profile_decision_sha256=profile_sha,
                created_utc="2026-09-07T15:30:00+00:00",
            )
            approval_sha = self._write_json(root / "approval.json", approval)

            plan = build_normalization_plan_proposal(
                quality,
                profile,
                approval,
                quality_audit_sha256=quality_sha,
                profile_decision_sha256=profile_sha,
                approval_sha256=approval_sha,
            )
            self.assertEqual(plan["status"], "linear_normalization_plan_proposal_ready")
            self.assertFalse(plan["policy"]["dynamic_fallback_allowed"])
            plan_sha = self._write_json(root / "plan.json", plan)

            authorization = build_normalization_execution_authorization(
                quality,
                profile,
                approval,
                plan,
                decision="APPROVE",
                actor="Guille",
                reason="E2E authorize only the gated linear normalization render.",
                quality_audit_sha256=quality_sha,
                profile_decision_sha256=profile_sha,
                approval_sha256=approval_sha,
                plan_sha256=plan_sha,
                created_utc="2026-09-07T15:31:00+00:00",
            )
            authorization_sha = self._write_json(root / "authorization.json", authorization)

            result = render_normalized_media(
                source,
                quality,
                profile,
                approval,
                plan,
                authorization,
                output,
                quality_audit_sha256=quality_sha,
                profile_decision_sha256=profile_sha,
                approval_sha256=approval_sha,
                plan_sha256=plan_sha,
                authorization_sha256=authorization_sha,
            )

            self.assertTrue(output.is_file())
            self.assertEqual(sha256_path(source), source_sha_before)
            self.assertEqual(result["status"], "normalization_render_complete")
            self.assertEqual(result["ffmpeg_loudnorm"]["normalization_type"], "linear")
            self.assertEqual(result["output"]["media"]["video_streams"], 1)
            self.assertEqual(result["output"]["media"]["audio_streams"], 1)
            self.assertLessEqual(
                abs(
                    result["output"]["media"]["duration_seconds"]
                    - result["source"]["media"]["duration_seconds"]
                ),
                0.15,
            )

            post = measure_audio_loudness(output)
            self.assertLessEqual(abs(post["integrated_lufs"] - (-23.0)), 0.5)
            self.assertLessEqual(post["true_peak_dbtp"], -1.0)
            self.assertTrue(result["technical_post_render_verification_required"])
            self.assertTrue(result["human_perceptual_review_required"])
            self.assertFalse(result["technical_pass"])
            self.assertFalse(result["human_pass"])
            self.assertFalse(result["auto_apply"])

            result_sha = self._write_json(root / "render_result.json", result)
            verification = build_normalization_post_render_verification(
                source,
                output,
                quality,
                profile,
                approval,
                plan,
                authorization,
                result,
                quality_audit_sha256=quality_sha,
                profile_decision_sha256=profile_sha,
                approval_sha256=approval_sha,
                plan_sha256=plan_sha,
                authorization_sha256=authorization_sha,
                render_result_sha256=result_sha,
            )
            self.assertEqual(verification["status"], "technical_normalization_pass")
            self.assertTrue(verification["valid_evidence"])
            self.assertTrue(verification["technical_pass"])
            self.assertEqual(verification["source"]["decoded_video_sha256"], verification["output"]["decoded_video_sha256"])
            self.assertEqual(verification["blockers"], [])
            self.assertTrue(verification["human_perceptual_review_required"])
            self.assertFalse(verification["human_pass"])
            self.assertFalse(verification["auto_apply"])


if __name__ == "__main__":
    unittest.main()
