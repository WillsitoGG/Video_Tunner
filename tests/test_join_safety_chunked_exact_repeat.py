import unittest

from video_tunner.join_safety import build_join_assessments
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming


CHUNKED_STRATEGY = "deterministic_overlap_12s_3s_v1"


def _transcript(segment_tokens, *, strategy="single_pass"):
    segments = []
    words = []
    cursor = 0.10
    for tokens in segment_tokens:
        segment_words = []
        for token in tokens:
            word = WordTiming(token, cursor, cursor + 0.20, 0.99)
            segment_words.append(word)
            words.append(word)
            cursor += 0.30
        segments.append(
            TranscriptSegment(
                text=" ".join(tokens),
                start=segment_words[0].start,
                end=segment_words[-1].end,
                words=tuple(segment_words),
            )
        )
        cursor += 0.40
    return (
        TranscriptResult(
            language="en",
            language_probability=0.99,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=tuple(segments),
            strategy=strategy,
            chunk_window_seconds=12.0 if strategy != "single_pass" else None,
            chunk_hop_seconds=3.0 if strategy != "single_pass" else None,
            chunk_count=len(segments) if strategy != "single_pass" else None,
        ),
        words,
    )


def _exact_repeat_candidate(words, start, size):
    end = start + size
    second_end = end + size
    first = " ".join(word.text for word in words[start:end])
    second = " ".join(word.text for word in words[end:second_end])
    gap = max(0.0, words[end].start - words[end - 1].end)
    return {
        "id": "possible_repetition-0001",
        "kind": "possible_repetition",
        "start": words[start].start,
        "end": words[end - 1].end,
        "confidence": 0.92,
        "reason": "Frase adyacente repetida; se conserva intacta la segunda lectura.",
        "evidence": {
            "word_start_index": start,
            "word_end_index_exclusive": end,
            "removed_text": first,
            "first_occurrence_text": first,
            "second_occurrence_text": second,
            "repeat_token_count": size,
            "gap_to_second_seconds": round(gap, 6),
            "keep_occurrence": "later",
        },
        "auto_apply": False,
    }


class ChunkedExactRepeatJoinBoundaryTests(unittest.TestCase):
    def test_chunked_exact_adjacent_repeat_does_not_block_on_segment_boundary_alone(self):
        transcript, words = _transcript(
            [["foo", "alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "qux"]],
            strategy=CHUNKED_STRATEGY,
        )
        candidate = _exact_repeat_candidate(words, 1, 3)
        result = build_join_assessments(transcript, [candidate])[0]
        self.assertEqual(result["status"], "join_context_only")
        self.assertTrue(result["evidence"]["segment_boundary"])
        self.assertTrue(
            result["evidence"]["segment_boundary_nonblocking_chunked_exact_repetition"]
        )
        self.assertFalse(result["safe_for_cut"])
        self.assertFalse(result["executable"])
        self.assertFalse(result["auto_apply"])

    def test_single_pass_exact_repeat_keeps_segment_boundary_blocker(self):
        transcript, words = _transcript(
            [["foo", "alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "qux"]],
            strategy="single_pass",
        )
        candidate = _exact_repeat_candidate(words, 1, 3)
        result = build_join_assessments(transcript, [candidate])[0]
        self.assertEqual(result["status"], "segment_boundary_risk")
        self.assertTrue(result["evidence"]["segment_boundary"])
        self.assertFalse(
            result["evidence"]["segment_boundary_nonblocking_chunked_exact_repetition"]
        )

    def test_chunked_non_exact_candidate_keeps_segment_boundary_blocker(self):
        transcript, words = _transcript(
            [["foo", "alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "qux"]],
            strategy=CHUNKED_STRATEGY,
        )
        candidate = _exact_repeat_candidate(words, 1, 3)
        candidate["evidence"]["second_occurrence_text"] = "alpha beta changed"
        result = build_join_assessments(transcript, [candidate])[0]
        self.assertEqual(result["status"], "segment_boundary_risk")
        self.assertFalse(
            result["evidence"]["segment_boundary_nonblocking_chunked_exact_repetition"]
        )

    def test_strong_punctuation_still_blocks_chunked_exact_repeat(self):
        transcript, words = _transcript(
            [["foo.", "alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "qux"]],
            strategy=CHUNKED_STRATEGY,
        )
        candidate = _exact_repeat_candidate(words, 1, 3)
        result = build_join_assessments(transcript, [candidate])[0]
        self.assertEqual(result["status"], "sentence_boundary_risk")
        self.assertTrue(result["evidence"]["punctuation_boundary"])
        self.assertTrue(
            result["evidence"]["segment_boundary_nonblocking_chunked_exact_repetition"]
        )

    def test_critical_lexical_context_still_blocks_chunked_exact_repeat(self):
        transcript, words = _transcript(
            [["not", "alpha", "beta", "gamma"], ["alpha", "beta", "gamma", "qux"]],
            strategy=CHUNKED_STRATEGY,
        )
        candidate = _exact_repeat_candidate(words, 1, 3)
        result = build_join_assessments(transcript, [candidate])[0]
        self.assertEqual(result["status"], "critical_lexical_context_risk")
        self.assertIn("not", result["evidence"]["critical_features_left"]["negations"])


if __name__ == "__main__":
    unittest.main()
