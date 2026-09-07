import math
import random
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from video_tunner.approval import sha256_path
from video_tunner.noise_audit import build_noise_evidence_audit
from video_tunner.tools import ToolNotFoundError, resolve_tool


class NoiseEvidenceAuditEndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.ffmpeg = resolve_tool("ffmpeg")
        except ToolNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    @staticmethod
    def _write_audio(path: Path) -> None:
        sample_rate = 48000
        duration = 8.0
        rng = random.Random(20260907)
        frames = bytearray()
        for index in range(int(sample_rate * duration)):
            t = index / sample_rate
            background = rng.randint(-100, 100)
            speech = (1.0 <= t < 2.0) or (4.0 <= t < 5.0)
            tone = int(4200 * math.sin(2.0 * math.pi * 440.0 * t)) if speech else 0
            value = max(-32768, min(32767, background + tone))
            frames += int(value).to_bytes(2, byteorder="little", signed=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(frames))

    def _make_media(self, wav_path: Path, output: Path) -> None:
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
                "color=c=black:s=320x240:r=25:d=8",
                "-i",
                str(wav_path),
                "-shortest",
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
                str(output),
            ],
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            self.fail(completed.stderr)

    @staticmethod
    def _quality(output: Path) -> dict:
        return {
            "schema_version": 1,
            "record_type": "audiovisual_quality_audit",
            "status": "quality_audit_complete",
            "valid": True,
            "phase2e_binding": {
                "required_status": "technical_post_render_pass",
                "technical_report_sha256": "a" * 64,
                "source_sha256": "b" * 64,
                "output_sha256": sha256_path(output),
                "join_count": 1,
            },
            "measurements": {},
            "findings": [],
            "summary": {"finding_count": 0, "risk_count": 0},
            "treatment_authorized": False,
            "auto_apply": False,
        }

    def test_real_encoded_media_yields_measurement_only_noise_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wav_path = root / "fixture.wav"
            output = root / "phase2e-output.mp4"
            self._write_audio(wav_path)
            self._make_media(wav_path, output)
            output_sha_before = sha256_path(output)

            report = build_noise_evidence_audit(
                output,
                self._quality(output),
                [(1.0, 2.0), (4.0, 5.0)],
                quality_audit_sha256="c" * 64,
                speech_evidence_sha256="d" * 64,
            )

            self.assertEqual(report["status"], "noise_measurement_complete")
            self.assertTrue(report["evidence_sufficient"])
            self.assertEqual(sha256_path(output), output_sha_before)
            non_speech = report["measurements"]["non_speech_energy"]
            speech = report["measurements"]["speech_energy"]
            self.assertIsInstance(non_speech["median_rms_dbfs"], float)
            self.assertIsInstance(speech["median_rms_dbfs"], float)
            self.assertGreater(speech["median_rms_dbfs"], non_speech["median_rms_dbfs"])
            self.assertGreater(report["measurements"]["speech_to_non_speech_median_rms_delta_db"], 10.0)
            self.assertFalse(report["treatment_policy"]["denoise_evaluated"])
            self.assertFalse(report["treatment_policy"]["denoise_authorized"])
            self.assertFalse(report["treatment_policy"]["filter_selected"])
            self.assertFalse(report["executable"])
            self.assertFalse(report["treatment_authorized"])
            self.assertFalse(report["auto_apply"])


if __name__ == "__main__":
    unittest.main()
