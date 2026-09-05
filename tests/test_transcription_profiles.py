import unittest
from unittest.mock import patch

from video_tunner.transcription import TranscriptResult
from video_tunner.transcription_profiles import (
    CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
    CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
    transcribe_audio_chunked_12s_3s,
)


class Deterministic123ProfileTests(unittest.TestCase):
    def test_profile_calls_existing_chunker_with_12s_3s_geometry_and_relabels_strategy(self):
        base = TranscriptResult(
            language="en",
            language_probability=0.99,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=(),
            strategy="deterministic_overlap_12s_6s_v1",
            chunk_window_seconds=12.0,
            chunk_hop_seconds=3.0,
            chunk_count=11,
        )
        with patch(
            "video_tunner.transcription_profiles.transcribe_audio_chunked",
            return_value=base,
        ) as chunked:
            result = transcribe_audio_chunked_12s_3s(
                "master.wav",
                model_name="large-v3-turbo",
                language="en",
                device="cpu",
                compute_type="int8",
            )

        chunked.assert_called_once_with(
            "master.wav",
            model_name="large-v3-turbo",
            language="en",
            device="cpu",
            compute_type="int8",
            window_seconds=12.0,
            hop_seconds=CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
        )
        self.assertEqual(result.strategy, CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY)
        self.assertEqual(result.chunk_window_seconds, 12.0)
        self.assertEqual(result.chunk_hop_seconds, 3.0)
        self.assertEqual(result.chunk_count, 11)


if __name__ == "__main__":
    unittest.main()
