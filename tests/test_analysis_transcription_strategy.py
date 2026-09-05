import inspect
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.analysis_pipeline import (
    CHUNKED_TRANSCRIPTION_STRATEGY,
    SINGLE_PASS_TRANSCRIPTION_STRATEGY,
    _transcribe_master_audio,
    analyze_spoken_video,
)
from video_tunner.cli import build_parser


class AnalysisTranscriptionStrategyTests(unittest.TestCase):
    def test_product_default_remains_single_pass(self):
        parameter = inspect.signature(analyze_spoken_video).parameters["transcription_strategy"]
        self.assertEqual(parameter.default, SINGLE_PASS_TRANSCRIPTION_STRATEGY)

    def test_cli_does_not_expose_unvalidated_strategy(self):
        args = build_parser().parse_args(["analyze", "video.mp4"])
        self.assertFalse(hasattr(args, "transcription_strategy"))

    def test_single_pass_routes_only_to_existing_transcriber(self):
        sentinel = object()
        with (
            patch("video_tunner.analysis_pipeline.transcribe_audio", return_value=sentinel) as single,
            patch("video_tunner.analysis_pipeline.transcribe_audio_chunked") as chunked,
        ):
            result = _transcribe_master_audio(
                Path("master.wav"),
                transcription_strategy=SINGLE_PASS_TRANSCRIPTION_STRATEGY,
                model_name="large-v3-turbo",
                language="en",
                device="cpu",
                compute_type="int8",
            )
        self.assertIs(result, sentinel)
        single.assert_called_once()
        chunked.assert_not_called()

    def test_chunked_strategy_routes_only_to_12_6_transcriber(self):
        sentinel = object()
        with (
            patch("video_tunner.analysis_pipeline.transcribe_audio") as single,
            patch("video_tunner.analysis_pipeline.transcribe_audio_chunked", return_value=sentinel) as chunked,
        ):
            result = _transcribe_master_audio(
                Path("master.wav"),
                transcription_strategy=CHUNKED_TRANSCRIPTION_STRATEGY,
                model_name="large-v3-turbo",
                language="en",
                device="cpu",
                compute_type="int8",
            )
        self.assertIs(result, sentinel)
        chunked.assert_called_once()
        single.assert_not_called()

    def test_unknown_strategy_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Estrategia de transcripción desconocida"):
            _transcribe_master_audio(
                Path("master.wav"),
                transcription_strategy="experimental_magic",
                model_name="large-v3-turbo",
                language="en",
                device="cpu",
                compute_type="int8",
            )


if __name__ == "__main__":
    unittest.main()
