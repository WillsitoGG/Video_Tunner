import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from video_tunner.approval import build_approval_record, sha256_path
from video_tunner.execution_authorization import build_execution_authorization
from video_tunner.media import probe_media
from video_tunner.plan_proposal import build_approved_edit_plan_proposal
from video_tunner.semantic_edit_plan import build_semantic_edit_plan
from video_tunner.semantic_render import render_semantic_plan


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe no disponibles")
class SemanticRenderEndToEndTests(unittest.TestCase):
    def test_exact_authorized_chain_renders_only_the_approved_semantic_span(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_semantic_e2e_") as temp:
            root = Path(temp)
            source = root / "semantic source.mp4"
            rendered = root / "semantic clean.mp4"
            analysis_path = root / "analysis.json"
            proposal_path = root / "approved_edit_plan_proposal.json"
            authorization_path = root / "semantic_execution_authorization.json"

            subprocess.run(
                [
                    shutil.which("ffmpeg"),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=160x120:rate=25:duration=10",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=10",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                check=True,
            )

            source_sha_before = sha256_path(source)
            source_probe = probe_media(source)
            target = {
                "source": "candidate_word_span",
                "text": "proyecto central listo",
                "start": 2.0,
                "end": 2.4,
                "word_start_index": 3,
                "word_end_index_exclusive": 6,
            }
            analysis = {
                "schema_version": 9,
                "source": {
                    "file": source.name,
                    "duration_seconds": source_probe["duration_seconds"],
                    "sha256": source_sha_before,
                },
                "mode": "conservative",
                "candidates": [
                    {
                        "id": "possible_repetition-0001",
                        "kind": "possible_repetition",
                        "start": 2.0,
                        "end": 2.4,
                    }
                ],
                "eligibility_assessments": [
                    {
                        "id": "eligibility-assessment-0001",
                        "candidate_id": "possible_repetition-0001",
                        "candidate_kind": "possible_repetition",
                        "status": "foundation_guards_pass",
                        "future_promotion_candidate": True,
                        "removed_text_validation": {"valid": True, **target},
                        "safe_for_cut": False,
                        "executable": False,
                        "auto_apply": False,
                    }
                ],
                "promotion_assessments": [
                    {
                        "id": "promotion-assessment-0001",
                        "eligibility_assessment_id": "eligibility-assessment-0001",
                        "candidate_id": "possible_repetition-0001",
                        "candidate_kind": "possible_repetition",
                        "mode": "conservative",
                        "status": "eligible_for_promotion_review",
                        "blockers": [],
                        "promotion_review_candidate": True,
                        "requires_explicit_approval": True,
                        "approval_state": "required",
                        "approved": False,
                        "target_preview": target,
                        "edit": None,
                        "safe_for_cut": False,
                        "executable": False,
                        "auto_apply": False,
                    }
                ],
            }
            analysis_path.write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
            analysis_sha = sha256_path(analysis_path)

            approval = build_approval_record(
                analysis,
                "promotion-assessment-0001",
                decision="APPROVE",
                actor="candidate-reviewer",
                reason="Synthetic exact repetition approved for render-gate E2E.",
                analysis_sha256=analysis_sha,
            )
            proposal = build_approved_edit_plan_proposal(
                analysis,
                [approval],
                analysis_sha256=analysis_sha,
            )
            self.assertEqual(proposal["status"], "proposal_ready_for_global_review")
            proposal_path.write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
            proposal_sha = sha256_path(proposal_path)

            authorization = build_execution_authorization(
                analysis,
                proposal,
                decision="APPROVE",
                actor="global-reviewer",
                reason="Synthetic bounded proposal authorized for render-gate E2E.",
                analysis_sha256=analysis_sha,
                proposal_sha256=proposal_sha,
            )
            authorization_path.write_text(json.dumps(authorization, indent=2) + "\n", encoding="utf-8")
            authorization_sha = sha256_path(authorization_path)

            plan = build_semantic_edit_plan(
                analysis,
                proposal,
                authorization,
                analysis_sha256=analysis_sha,
                proposal_sha256=proposal_sha,
                authorization_sha256=authorization_sha,
            )
            self.assertEqual(plan["summary"]["edit_count"], 1)
            self.assertAlmostEqual(plan["summary"]["removed_seconds"], 0.4, places=6)
            self.assertFalse(plan["auto_apply"])

            result = render_semantic_plan(
                source,
                analysis,
                proposal,
                authorization,
                plan,
                rendered,
                analysis_sha256=analysis_sha,
                proposal_sha256=proposal_sha,
                authorization_sha256=authorization_sha,
            )
            self.assertEqual(result, rendered.resolve())
            self.assertTrue(rendered.is_file())
            self.assertEqual(sha256_path(source), source_sha_before)

            rendered_probe = probe_media(rendered)
            expected_duration = float(source_probe["duration_seconds"]) - 0.4
            self.assertAlmostEqual(rendered_probe["duration_seconds"], expected_duration, delta=0.15)
            self.assertEqual(rendered_probe["video_streams"], 1)
            self.assertEqual(rendered_probe["audio_streams"], 1)
            self.assertNotEqual(hashlib.sha256(rendered.read_bytes()).hexdigest(), source_sha_before)


if __name__ == "__main__":
    unittest.main()
