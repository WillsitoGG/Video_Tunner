import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.analysis_pipeline import analyze_spoken_video
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming
from video_tunner.vad import SpeechInterval


class AnalysisPipelineTests(unittest.TestCase):
    def test_pipeline_writes_all_artifacts_without_turning_candidates_into_edits(self):
        transcript = TranscriptResult(
            language="es",
            language_probability=0.99,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=(
                TranscriptSegment(
                    text="Hola eh seguimos",
                    start=0.1,
                    end=2.5,
                    words=(
                        WordTiming("Hola", 0.1, 0.5, 0.99),
                        WordTiming("eh", 0.6, 0.9, 0.90),
                        WordTiming("seguimos", 1.8, 2.5, 0.98),
                    ),
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "video source.mp4"
            source.write_bytes(b"fake-video")
            output = root / "out"

            def fake_extract(_source, destination, **_kwargs):
                path = Path(destination)
                path.write_bytes(b"fake-wav")
                return path

            with (
                patch("video_tunner.analysis_pipeline.probe_media", return_value={"duration_seconds": 3.0, "audio_streams": 1}),
                patch("video_tunner.analysis_pipeline.extract_analysis_audio", side_effect=fake_extract),
                patch("video_tunner.analysis_pipeline.transcribe_audio", return_value=transcript),
                patch("video_tunner.analysis_pipeline.detect_speech", return_value=[SpeechInterval(0.05, 1.0), SpeechInterval(1.75, 2.7)]),
            ):
                result = analyze_spoken_video(source, output, mode="conservative", language="es")

            for key in ("analysis", "transcript_json", "transcript_txt", "subtitles_srt"):
                self.assertTrue(Path(result[key]).is_file(), key)
            analysis_text = Path(result["analysis"]).read_text(encoding="utf-8")
            self.assertIn('"automatic_edits": 0', analysis_text)
            self.assertIn('"auto_apply": false', analysis_text)
            self.assertFalse(any(p.name.startswith(".video_tunner_analysis_") for p in output.iterdir()))


if __name__ == "__main__":
    unittest.main()
