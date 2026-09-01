import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_tunner.media import probe_media


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe no disponibles")
class FfmpegEndToEndTests(unittest.TestCase):
    def test_clean_removes_synthetic_silence_and_renders_valid_mp4(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_") as temp:
            root = Path(temp)
            source = root / "sample input.mp4"
            output_dir = root / "output with spaces"

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
                    "color=c=black:s=320x240:r=25:d=3",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "anullsrc=r=48000:cl=mono:d=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=660:sample_rate=48000:duration=1",
                    "-filter_complex",
                    "[1:a][2:a][3:a]concat=n=3:v=0:a=1[a]",
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
                    "-shortest",
                    str(source),
                ],
                check=True,
            )

            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "video_tunner",
                    "clean",
                    str(source),
                    "--mode",
                    "conservative",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
            )

            rendered = output_dir / "sample input_clean.mp4"
            plan_path = output_dir / "sample input_edit_plan.json"
            self.assertTrue(rendered.is_file())
            self.assertTrue(plan_path.is_file())

            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual(plan["summary"]["edit_count"], 1)
            self.assertGreater(plan["summary"]["removed_seconds"], 0.6)

            rendered_probe = probe_media(rendered)
            self.assertGreater(rendered_probe["duration_seconds"], 2.0)
            self.assertLess(rendered_probe["duration_seconds"], 2.4)
            self.assertEqual(rendered_probe["video_streams"], 1)
            self.assertEqual(rendered_probe["audio_streams"], 1)


if __name__ == "__main__":
    unittest.main()
