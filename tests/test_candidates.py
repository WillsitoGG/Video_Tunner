import tempfile
import unittest
from pathlib import Path

from video_tunner.candidates import build_analysis_report, build_candidates
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming
from video_tunner.vad import SpeechInterval


def sample_transcript() -> TranscriptResult:
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text="Hola eh seguimos ahora",
                start=0.2,
                end=3.2,
                words=(
                    WordTiming("Hola", 0.2, 0.6, 0.99),
                    WordTiming("eh", 0.7, 1.0, 0.90),
                    WordTiming("seguimos", 2.0, 2.5, 0.98),
                    WordTiming("ahora", 2.6, 3.2, 0.97),
                ),
            ),
        ),
    )


class CandidateTests(unittest.TestCase):
    def test_candidates_never_auto_apply(self):
        candidates = build_candidates(
            sample_transcript(),
            [SpeechInterval(0.15, 1.05), SpeechInterval(1.95, 3.25)],
            duration=3.5,
            mode="conservative",
        )
        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(all(candidate["decision"] == "undecided" for candidate in candidates))
        self.assertTrue(all(candidate["auto_apply"] is False for candidate in candidates))

    def test_vad_gap_is_enriched_with_word_context(self):
        candidates = build_candidates(
            sample_transcript(),
            [SpeechInterval(0.15, 1.05), SpeechInterval(1.95, 3.25)],
            duration=3.5,
            mode="conservative",
        )
        pause = next(c for c in candidates if c["kind"] == "pause" and c["start"] < 1.2 < c["end"])
        self.assertTrue(pause["evidence"]["silero_vad"])
        self.assertTrue(pause["evidence"]["word_gap"])
        self.assertEqual(pause["evidence"]["before_word"], "eh")
        self.assertEqual(pause["evidence"]["after_word"], "seguimos")

    def test_obvious_filler_is_review_only_and_not_semantically_assumed(self):
        candidates = build_candidates(
            sample_transcript(),
            [SpeechInterval(0.15, 3.25)],
            duration=3.5,
            mode="conservative",
        )
        filler = next(c for c in candidates if c["kind"] == "possible_filler")
        self.assertEqual(filler["evidence"]["token"], "eh")
        self.assertIsNone(filler["confidence"])
        self.assertEqual(filler["decision"], "undecided")

    def test_analysis_report_hashes_source_and_records_no_automatic_edits(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "sample.mp4"
            source.write_bytes(b"test-source")
            transcript = sample_transcript()
            speech = [SpeechInterval(0.15, 3.25)]
            candidates = build_candidates(transcript, speech, duration=3.5, mode="conservative")
            report = build_analysis_report(
                source,
                {"duration_seconds": 3.5},
                transcript,
                speech,
                mode="conservative",
                candidates=candidates,
            )
            self.assertEqual(len(report["source"]["sha256"]), 64)
            self.assertEqual(report["summary"]["automatic_edits"], 0)
            self.assertTrue(report["safety"]["candidates_are_not_edits"])


if __name__ == "__main__":
    unittest.main()
