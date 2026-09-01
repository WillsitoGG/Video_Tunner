import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.vad import detect_speech


class FasterWhisperVadBackendTests(unittest.TestCase):
    def test_detect_speech_converts_sample_offsets_to_seconds(self):
        package = types.ModuleType("faster_whisper")
        package.__path__ = []
        audio_module = types.ModuleType("faster_whisper.audio")
        vad_module = types.ModuleType("faster_whisper.vad")

        audio_module.decode_audio = lambda *_args, **_kwargs: object()

        class FakeVadOptions:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        vad_module.VadOptions = FakeVadOptions
        vad_module.get_speech_timestamps = lambda *_args, **_kwargs: [
            {"start": 1600, "end": 3200},
            {"start": 8000, "end": 16000},
        ]

        with tempfile.TemporaryDirectory() as temp:
            wav = Path(temp) / "audio.wav"
            wav.write_bytes(b"RIFF")
            with patch.dict(
                sys.modules,
                {
                    "faster_whisper": package,
                    "faster_whisper.audio": audio_module,
                    "faster_whisper.vad": vad_module,
                },
            ):
                intervals = detect_speech(wav)

        self.assertEqual([(x.start, x.end) for x in intervals], [(0.1, 0.2), (0.5, 1.0)])


if __name__ == "__main__":
    unittest.main()
