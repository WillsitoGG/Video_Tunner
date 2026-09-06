import unittest
from unittest.mock import patch

from video_tunner.transcription import TranscriptResult
from video_tunner.transcription_profiles import (
    CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
    CHUNKED_TRANSCRIPTION_12S_3S_OWNERSHIP_STRATEGY,
    CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
    transcribe_audio_chunked_12s_3s,
)


class RepeatConsensus123ProfileTests(unittest.TestCase):
    def test_strategy_name_explicitly_distinguishes_consensus_from_ownership(self):
        self.assertEqual(
            CHUNKED_TRANSCRIPTION_12S_3S_OWNERSHIP_STRATEGY,
            "deterministic_overlap_12s_3s_v1",
        )
        self.assertEqual(
            CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
            "deterministic_overlap_12s_3s_repeat_consensus_v1",
        )
        self.assertNotEqual(
            CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
            CHUNKED_TRANSCRIPTION_12S_3S_OWNERSHIP_STRATEGY,
        )

    def test_profile_calls_consensus_chunker_with_12s_3s_geometry_and_auditable_strategy(self):
        result_value = TranscriptResult(
            language="en",
            language_probability=0.99,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=(),
            strategy=CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
            chunk_window_seconds=12.0,
            chunk_hop_seconds=3.0,
            chunk_count=11,
        )
        with patch(
            "video_tunner.transcription_profiles.transcribe_audio_chunked_with_repeat_consensus",
            return_value=result_value,
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
            strategy=CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
        )
        self.assertIs(result, result_value)


if __name__ == "__main__":
    unittest.main()
