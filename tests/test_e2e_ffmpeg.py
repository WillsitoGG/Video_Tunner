import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

from video_tunner.audio import extract_analysis_audio
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

    def test_extract_analysis_audio_is_16khz_mono_pcm(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_audio_") as temp:
            root = Path(temp)
            source = root / "audio source.mp4"
            wav = root / "analysis audio.wav"
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
                    "color=c=black:s=160x120:r=25:d=1",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=1",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "libx264",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(source),
                ],
                check=True,
            )
            extract_analysis_audio(source, wav)
            with wave.open(str(wav), "rb") as handle:
                self.assertEqual(handle.getnchannels(), 1)
                self.assertEqual(handle.getframerate(), 16000)
                self.assertEqual(handle.getsampwidth(), 2)


if __name__ == "__main__":
    unittest.main()
