import json
import tempfile
import unittest
from pathlib import Path

from video_tunner.transcription import (
    TranscriptResult,
    TranscriptSegment,
    WordTiming,
    _srt_timestamp,
    transcript_to_dict,
    write_srt,
    write_transcript_json,
    write_transcript_txt,
)


class TranscriptionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.result = TranscriptResult(
            language="es",
            language_probability=0.98,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=(
                TranscriptSegment(
                    text="Hola mundo.",
                    start=0.4,
                    end=1.6,
                    words=(
                        WordTiming("Hola", 0.4, 0.8, 0.99),
                        WordTiming("mundo.", 0.9, 1.6, 0.97),
                    ),
                ),
                TranscriptSegment(
                    text="Seguimos.",
                    start=2.2,
                    end=3.0,
                    words=(WordTiming("Seguimos.", 2.2, 3.0, 0.95),),
                ),
            ),
        )

    def test_transcript_dict_preserves_word_timestamps(self):
        payload = transcript_to_dict(self.result)
        self.assertEqual(payload["word_count"], 3)
        self.assertEqual(payload["segments"][0]["words"][1]["text"], "mundo.")
        self.assertEqual(payload["segments"][0]["words"][1]["start"], 0.9)

    def test_txt_json_and_srt_are_written(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            txt = write_transcript_txt(self.result, root / "transcript.txt")
            js = write_transcript_json(self.result, root / "transcript.json")
            srt = write_srt(self.result, root / "subtitles.srt")
            self.assertEqual(txt.read_text(encoding="utf-8"), "Hola mundo. Seguimos.\n")
            self.assertEqual(json.loads(js.read_text(encoding="utf-8"))["language"], "es")
            srt_text = srt.read_text(encoding="utf-8")
            self.assertIn("00:00:00,400 --> 00:00:01,600", srt_text)
            self.assertIn("Hola mundo.", srt_text)

    def test_srt_timestamp_rounds_to_milliseconds(self):
        self.assertEqual(_srt_timestamp(3661.2346), "01:01:01,235")


if __name__ == "__main__":
    unittest.main()
