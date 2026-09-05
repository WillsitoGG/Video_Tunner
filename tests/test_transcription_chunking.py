import unittest

from video_tunner.transcription import (
    CHUNKED_TRANSCRIPTION_STRATEGY,
    TranscriptResult,
    TranscriptSegment,
    TranscriptionChunkWindow,
    WordTiming,
    build_transcription_chunk_windows,
    merge_chunked_transcript_segments,
    transcript_to_dict,
)


def segment(*words: WordTiming) -> TranscriptSegment:
    return TranscriptSegment(
        text=" ".join(word.text for word in words),
        start=words[0].start,
        end=words[-1].end,
        words=tuple(words),
    )


class DeterministicChunkWindowTests(unittest.TestCase):
    def test_12_6_ownership_tiles_timeline_without_overlap(self):
        windows = build_transcription_chunk_windows(25.0)
        self.assertEqual(
            [(item.start, item.end) for item in windows],
            [(0.0, 12.0), (6.0, 18.0), (12.0, 24.0), (18.0, 25.0)],
        )
        self.assertEqual(
            [(item.ownership_start, item.ownership_end) for item in windows],
            [(0.0, 9.0), (9.0, 15.0), (15.0, 21.0), (21.0, 25.0)],
        )
        for left, right in zip(windows, windows[1:]):
            self.assertEqual(left.ownership_end, right.ownership_start)

    def test_short_audio_is_one_owned_window(self):
        windows = build_transcription_chunk_windows(8.5)
        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].start, 0.0)
        self.assertEqual(windows[0].end, 8.5)
        self.assertEqual(windows[0].ownership_start, 0.0)
        self.assertEqual(windows[0].ownership_end, 8.5)

    def test_invalid_geometry_fails_closed(self):
        with self.assertRaises(ValueError):
            build_transcription_chunk_windows(10.0, window_seconds=6.0, hop_seconds=7.0)
        with self.assertRaises(ValueError):
            build_transcription_chunk_windows(-1.0)


class DeterministicChunkMergeTests(unittest.TestCase):
    def test_overlap_hypotheses_are_not_duplicated(self):
        first = TranscriptionChunkWindow(0, 0.0, 12.0, 0.0, 9.0)
        second = TranscriptionChunkWindow(1, 6.0, 18.0, 9.0, 18.0)
        merged = merge_chunked_transcript_segments(
            [
                (
                    first,
                    (
                        segment(
                            WordTiming("before", 8.0, 8.4, 0.9),
                            WordTiming("duplicate", 9.3, 9.7, 0.8),
                        ),
                    ),
                ),
                (
                    second,
                    (
                        segment(
                            WordTiming("overlap-copy", 2.0, 2.4, 0.7),
                            WordTiming("after", 3.2, 3.6, 0.95),
                        ),
                    ),
                ),
            ]
        )
        words = [word for item in merged for word in item.words]
        self.assertEqual([word.text for word in words], ["before", "after"])
        self.assertEqual([word.start for word in words], [8.0, 9.2])

    def test_phrase_can_cross_ownership_boundary_without_gap_or_duplicate(self):
        first = TranscriptionChunkWindow(0, 0.0, 12.0, 0.0, 9.0)
        second = TranscriptionChunkWindow(1, 6.0, 18.0, 9.0, 18.0)
        merged = merge_chunked_transcript_segments(
            [
                (first, (segment(WordTiming("hello", 8.4, 8.8, 0.95)),)),
                (second, (segment(WordTiming("world", 3.1, 3.5, 0.96)),)),
            ]
        )
        words = [word for item in merged for word in item.words]
        self.assertEqual([word.text for word in words], ["hello", "world"])
        self.assertLess(words[0].end, words[1].start)

    def test_global_timestamps_are_shifted_from_local_chunk_time(self):
        window = TranscriptionChunkWindow(2, 12.0, 24.0, 15.0, 21.0)
        merged = merge_chunked_transcript_segments(
            [(window, (segment(WordTiming("global", 4.0, 4.5, 0.99)),))]
        )
        word = merged[0].words[0]
        self.assertEqual(word.start, 16.0)
        self.assertEqual(word.end, 16.5)

    def test_last_window_owns_right_edge(self):
        window = TranscriptionChunkWindow(1, 6.0, 13.0, 9.0, 13.0)
        merged = merge_chunked_transcript_segments(
            [(window, (segment(WordTiming("end", 6.7, 7.0, 0.9)),))]
        )
        self.assertEqual(merged[0].words[0].text, "end")
        self.assertEqual(merged[0].words[0].end, 13.0)


class ChunkedTranscriptAuditTests(unittest.TestCase):
    def test_strategy_metadata_is_serialized(self):
        result = TranscriptResult(
            language="en",
            language_probability=0.99,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=(segment(WordTiming("hello", 0.1, 0.5, 0.9)),),
            strategy=CHUNKED_TRANSCRIPTION_STRATEGY,
            chunk_window_seconds=12.0,
            chunk_hop_seconds=6.0,
            chunk_count=4,
        )
        payload = transcript_to_dict(result)
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["strategy"]["name"], CHUNKED_TRANSCRIPTION_STRATEGY)
        self.assertEqual(payload["strategy"]["chunk_window_seconds"], 12.0)
        self.assertEqual(payload["strategy"]["chunk_hop_seconds"], 6.0)
        self.assertEqual(payload["strategy"]["chunk_count"], 4)


if __name__ == "__main__":
    unittest.main()
