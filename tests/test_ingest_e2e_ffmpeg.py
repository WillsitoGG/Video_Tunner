from __future__ import annotations

import json
import math
import random
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from video_tunner.ingest import ingest_video, materialize_external_master


FFMPEG = shutil.which("ffmpeg")
FFPROBE = shutil.which("ffprobe")


@unittest.skipUnless(FFMPEG and FFPROBE, "FFmpeg/ffprobe no disponibles")
class IngestFfmpegRegressionTests(unittest.TestCase):
    @staticmethod
    def _duration(path: Path) -> float:
        completed = subprocess.run(
            [
                str(FFPROBE),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(completed.stdout.strip())

    @staticmethod
    def _amplitudes(duration: float, *, blocks_per_second: int = 5) -> list[float]:
        rng = random.Random(20260902)
        return [rng.uniform(0.08, 0.95) for _ in range(int(duration * blocks_per_second) + 8)]

    @classmethod
    def _write_timeline_wave(
        cls,
        path: Path,
        *,
        duration: float,
        amplitudes: list[float],
        offset_seconds: float = 0.0,
        time_scale: float = 1.0,
        sample_rate: int = 8000,
        blocks_per_second: int = 5,
    ) -> None:
        """Write audio whose local time u maps to video time t=offset+scale*u."""
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            frames = bytearray()
            for index in range(int(duration * sample_rate)):
                local_time = index / sample_rate
                video_time = offset_seconds + time_scale * local_time
                if video_time < 0:
                    sample = 0
                else:
                    block = min(int(video_time * blocks_per_second), len(amplitudes) - 1)
                    amplitude = amplitudes[block]
                    carrier = (
                        0.72 * math.sin(2.0 * math.pi * 317.0 * video_time)
                        + 0.28 * math.sin(2.0 * math.pi * 619.0 * video_time)
                    )
                    sample = int(max(-1.0, min(1.0, amplitude * carrier)) * 29000)
                frames.extend(struct.pack("<h", sample))
            handle.writeframes(frames)

    @staticmethod
    def _write_silence(path: Path, duration: float, sample_rate: int = 8000) -> None:
        with wave.open(str(path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(sample_rate)
            handle.writeframes(b"\x00\x00" * int(duration * sample_rate))

    @staticmethod
    def _make_video(video: Path, *, duration: float, camera_audio: Path | None) -> None:
        command = [
            str(FFMPEG),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=160x120:r=25:d={duration}",
        ]
        if camera_audio is not None:
            command.extend(
                [
                    "-i",
                    str(camera_audio),
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                ]
            )
        else:
            command.extend(
                [
                    "-t",
                    str(duration),
                    "-an",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                ]
            )
        command.append(str(video))
        subprocess.run(command, capture_output=True, text=True, check=True)

    def test_positive_offset_master_matches_video_timeline_exactly(self):
        """Regression: indefinite apad + timestamp atrim produced 3.256s, not 4s."""
        with tempfile.TemporaryDirectory(prefix="video_tunner_master_timeline_") as temp:
            root = Path(temp)
            external = root / "external recorder.wav"
            master = root / "master audio.flac"
            amplitudes = self._amplitudes(4.0)
            self._write_timeline_wave(external, duration=3.0, amplitudes=amplitudes)

            materialize_external_master(
                external,
                master,
                video_duration=4.0,
                offset_seconds=1.0,
                time_scale=1.0,
            )
            self.assertAlmostEqual(self._duration(master), 4.0, delta=0.03)

    def test_auto_sync_recovers_negative_offset_and_materializes_full_master(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_negative_offset_") as temp:
            root = Path(temp)
            camera = root / "camera reference.wav"
            external = root / "external recorder starts early.wav"
            video = root / "video with camera audio.mp4"
            output = root / "output with spaces"
            video_duration = 30.0
            expected_offset = -1.0
            amplitudes = self._amplitudes(video_duration)

            self._write_timeline_wave(camera, duration=video_duration, amplitudes=amplitudes)
            self._write_timeline_wave(
                external,
                duration=video_duration - expected_offset,
                amplitudes=amplitudes,
                offset_seconds=expected_offset,
            )
            self._make_video(video, duration=video_duration, camera_audio=camera)

            result = ingest_video(video, output, external_audio=external)
            self.assertEqual(result["status"], "ready_auto")
            report = json.loads(Path(result["ingest_report"]).read_text(encoding="utf-8"))
            self.assertAlmostEqual(report["sync"]["offset_seconds"], expected_offset, delta=0.12)
            self.assertGreaterEqual(report["sync"]["confidence"], 0.65)
            self.assertGreaterEqual(len(report["sync"]["anchors"]), 3)
            self.assertAlmostEqual(self._duration(Path(result["master_audio"])), video_duration, delta=0.05)

    def test_auto_sync_recovers_media_level_drift(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_drift_") as temp:
            root = Path(temp)
            camera = root / "camera drift reference.wav"
            external = root / "external drifting recorder.wav"
            video = root / "video drift reference.mp4"
            output = root / "output drift"
            video_duration = 90.0
            expected_offset = 0.6
            expected_scale = 1.001
            expected_drift_ppm = 1000.0
            external_duration = (video_duration - expected_offset) / expected_scale
            amplitudes = self._amplitudes(video_duration)

            self._write_timeline_wave(camera, duration=video_duration, amplitudes=amplitudes)
            self._write_timeline_wave(
                external,
                duration=external_duration,
                amplitudes=amplitudes,
                offset_seconds=expected_offset,
                time_scale=expected_scale,
            )
            self._make_video(video, duration=video_duration, camera_audio=camera)

            result = ingest_video(video, output, external_audio=external)
            self.assertEqual(result["status"], "ready_auto")
            report = json.loads(Path(result["ingest_report"]).read_text(encoding="utf-8"))
            self.assertAlmostEqual(report["sync"]["offset_seconds"], expected_offset, delta=0.18)
            self.assertAlmostEqual(report["sync"]["drift_ppm"], expected_drift_ppm, delta=450.0)
            self.assertGreaterEqual(report["sync"]["confidence"], 0.65)
            self.assertLessEqual(report["sync"]["residual_rms_seconds"], 0.08)
            self.assertAlmostEqual(self._duration(Path(result["master_audio"])), video_duration, delta=0.05)

    def test_flat_signal_requires_review_and_never_materializes_master(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_flat_sync_") as temp:
            root = Path(temp)
            camera = root / "silent camera.wav"
            external = root / "silent external.wav"
            video = root / "silent reference.mp4"
            output = root / "output"

            self._write_silence(camera, 10.0)
            self._write_silence(external, 10.0)
            self._make_video(video, duration=10.0, camera_audio=camera)

            result = ingest_video(video, output, external_audio=external)
            self.assertEqual(result["status"], "review_required")
            self.assertIsNone(result["master_audio"])
            report = json.loads(Path(result["ingest_report"]).read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "review_required")
            self.assertIsNone(report["master_audio"])
            self.assertTrue(report["review_reasons"])

    def test_manual_override_works_without_camera_audio_and_reports_partial_coverage(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_manual_sync_") as temp:
            root = Path(temp)
            external = root / "external only.wav"
            video = root / "video without audio.mp4"
            output = root / "manual output"
            amplitudes = self._amplitudes(5.0)

            self._write_timeline_wave(external, duration=4.0, amplitudes=amplitudes)
            self._make_video(video, duration=5.0, camera_audio=None)

            result = ingest_video(
                video,
                output,
                external_audio=external,
                manual_offset_seconds=1.0,
            )
            self.assertEqual(result["status"], "ready_manual")
            report = json.loads(Path(result["ingest_report"]).read_text(encoding="utf-8"))
            self.assertEqual(report["sync"]["method"], "manual_override")
            self.assertAlmostEqual(report["coverage"]["coverage_ratio"], 0.8, delta=0.01)
            self.assertTrue(report["warnings"])
            self.assertAlmostEqual(self._duration(Path(result["master_audio"])), 5.0, delta=0.05)


if __name__ == "__main__":
    unittest.main()
