import subprocess
import tempfile
import unittest
from pathlib import Path

from video_tunner.approval import sha256_path
from video_tunner.audiovisual_quality import build_audiovisual_quality_audit
from video_tunner.tools import ToolNotFoundError, resolve_tool


class AudiovisualQualityAuditEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = resolve_tool("ffmpeg")
        except ToolNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def _make_media(self, path: Path, *, volume: float) -> None:
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
                "color=c=black:s=320x240:r=25:d=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=3",
                "-filter:a",
                f"volume={volume}",
                "-shortest",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            self.fail(completed.stderr)

    def test_real_ffmpeg_measurement_builds_non_executable_quality_audit(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            output = root / "output.mp4"
            self._make_media(source, volume=0.20)
            self._make_media(output, volume=0.16)
            technical = {
                "schema_version": 1,
                "record_type": "semantic_render_verification",
                "status": "technical_post_render_pass",
                "technical_pass": True,
                "blockers": [],
                "source": {"sha256": sha256_path(source)},
                "output": {"sha256": sha256_path(output)},
                "post_render_join_audits": [
                    {
                        "id": "post-render-join-0001",
                        "status": "acoustic_context_only",
                        "technical_pass": True,
                    }
                ],
                "auto_apply": False,
            }
            audit = build_audiovisual_quality_audit(
                source,
                output,
                technical,
                technical_report_sha256="f" * 64,
            )
            source_audio = audit["measurements"]["source_audio"]
            output_audio = audit["measurements"]["output_audio"]
            self.assertIsInstance(source_audio["integrated_lufs"], float)
            self.assertIsInstance(source_audio["true_peak_dbtp"], float)
            self.assertIsInstance(output_audio["integrated_lufs"], float)
            self.assertIsInstance(output_audio["true_peak_dbtp"], float)
            self.assertLess(output_audio["integrated_lufs"], source_audio["integrated_lufs"])
            self.assertEqual(audit["status"], "quality_audit_complete")
            self.assertFalse(audit["treatment_authorized"])
            self.assertFalse(audit["auto_apply"])


if __name__ == "__main__":
    unittest.main()
