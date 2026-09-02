from __future__ import annotations

import random
import shutil
import struct
import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

from video_tunner.ingest import materialize_external_master


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg/ffprobe no disponibles")
class IngestFfmpegRegressionTests(unittest.TestCase):
    def test_positive_offset_master_matches_video_timeline_exactly(self):
        """Regression: indefinite apad + timestamp atrim produced 3.256s, not 4s."""
        with tempfile.TemporaryDirectory(prefix="video_tunner_master_timeline_") as temp:
            root = Path(temp)
            external = root / "external recorder.wav"
            master = root / "master audio.flac"
            sample_rate = 8000
            duration = 3.0
            rng = random.Random(20260902)

            with wave.open(str(external), "wb") as handle:
                handle.setnchannels(1)
                handle.setsampwidth(2)
                handle.setframerate(sample_rate)
                frames = bytearray()
                for _ in range(int(duration * sample_rate)):
                    frames.extend(struct.pack("<h", int(rng.uniform(-0.7, 0.7) * 30000)))
                handle.writeframes(frames)

            materialize_external_master(
                external,
                master,
                video_duration=4.0,
                offset_seconds=1.0,
                time_scale=1.0,
            )

            completed = subprocess.run(
                [
                    str(shutil.which("ffprobe")),
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=nw=1:nk=1",
                    str(master),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertAlmostEqual(float(completed.stdout.strip()), 4.0, delta=0.03)


if __name__ == "__main__":
    unittest.main()
