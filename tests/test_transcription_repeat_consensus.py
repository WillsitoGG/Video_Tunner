import unittest

from video_tunner.transcription import (
    TranscriptSegment,
    TranscriptionChunkWindow,
    WordTiming,
    merge_chunked_transcript_segments,
)
from video_tunner.transcription_consensus import (
    REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS,
    merge_chunked_transcript_segments_with_repeat_consensus,
)


PHRASE = ("and", "then", "you", "can")
CONTEXT = ("add", "the", "colors")


def segment(*words: WordTiming) -> TranscriptSegment:
    return TranscriptSegment(
        text=" ".join(word.text for word in words),
        start=words[0].start,
        end=words[-1].end,
        words=tuple(words),
    )


def local_phrase(window_start: float, global_start: float, *, probability: float = 0.95):
    starts = [global_start + (index * 0.20) for index in range(4)]
    return tuple(
        WordTiming(
            text=token,
            start=round(start - window_start, 6),
            end=round(start + 0.16 - window_start, 6),
            probability=probability,
        )
        for token, start in zip(PHRASE, starts)
    )


def repeat_words(window_start: float, *, shift: float = 0.0, probability: float = 0.95):
    return (
        *local_phrase(window_start, 20.00 + shift, probability=probability),
        *local_phrase(window_start, 20.85 + shift, probability=probability),
    )


def collapsed_phrase(window_start: float, *, probability: float = 0.98):
    global_spans = (
        ("and", 20.05, 20.21),
        ("then", 20.25, 20.41),
        ("you", 20.45, 20.61),
        ("can", 20.65, 21.86),
    )
    return tuple(
        WordTiming(
            text=text,
            start=round(start - window_start, 6),
            end=round(end - window_start, 6),
            probability=probability,
        )
        for text, start, end in global_spans
    )


def owner_context(window_start: float):
    global_spans = (
        ("add", 21.90, 22.08, 0.88),
        ("the", 22.08, 22.30, 0.72),
        ("colors", 22.30, 22.58, 0.79),
    )
    return tuple(
        WordTiming(
            text=text,
            start=round(start - window_start, 6),
            end=round(end - window_start, 6),
            probability=probability,
        )
        for text, start, end, probability in global_spans
    )


def windows():
    return (
        TranscriptionChunkWindow(4, 12.0, 24.0, 16.5, 19.5),
        TranscriptionChunkWindow(5, 15.0, 27.0, 19.5, 22.5),
        TranscriptionChunkWindow(6, 18.0, 30.0, 22.5, 25.5),
    )


def flat_words(segments):
    return [word for item in segments for word in item.words]


def flat_text(segments):
    return [word.text for word in flat_words(segments)]


class RepeatConsensusMergeTests(unittest.TestCase):
    def test_timing_tolerance_remains_precommitted_035_seconds(self):
        self.assertEqual(REPEAT_CONSENSUS_TIMING_TOLERANCE_SECONDS, 0.35)

    def test_298_like_collapsed_owner_repeat_is_recovered_without_losing_context(self):
        left, owner, right = windows()
        context = owner_context(owner.start)
        chunks = [
            (left, (segment(*repeat_words(left.start, probability=0.94)),)),
            (owner, (segment(*collapsed_phrase(owner.start), *context),)),
            (right, (segment(*repeat_words(right.start, probability=0.96)),)),
        ]

        baseline = merge_chunked_transcript_segments(chunks)
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)

        self.assertEqual(flat_text(baseline), list(PHRASE + CONTEXT))
        self.assertEqual(flat_text(consensus), list(PHRASE + PHRASE + CONTEXT))

        context_after = flat_words(consensus)[-len(CONTEXT) :]
        self.assertEqual([word.text for word in context_after], list(CONTEXT))
        self.assertEqual(
            [(word.start, word.end, word.probability) for word in context_after],
            [
                (21.90, 22.08, 0.88),
                (22.08, 22.30, 0.72),
                (22.30, 22.58, 0.79),
            ],
        )

    def test_single_supporter_cannot_invent_repeat(self):
        left, owner, right = windows()
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (owner, (segment(*collapsed_phrase(owner.start)),)),
            (right, (segment(*local_phrase(right.start, 20.85)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), list(PHRASE))

    def test_same_side_supporters_do_not_override_owner(self):
        left = TranscriptionChunkWindow(3, 9.0, 21.0, 13.5, 16.5)
        near_left = TranscriptionChunkWindow(4, 12.0, 24.0, 16.5, 19.5)
        owner = TranscriptionChunkWindow(5, 15.0, 27.0, 19.5, 22.5)
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (near_left, (segment(*repeat_words(near_left.start)),)),
            (owner, (segment(*collapsed_phrase(owner.start)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), list(PHRASE))

    def test_timing_disagreement_fails_closed(self):
        left, owner, right = windows()
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (owner, (segment(*collapsed_phrase(owner.start)),)),
            (right, (segment(*repeat_words(right.start, shift=0.8)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), list(PHRASE))

    def test_owner_lexical_disagreement_fails_closed(self):
        left, owner, right = windows()
        divergent = (
            WordTiming("and", 5.05, 5.21, 0.98),
            WordTiming("then", 5.25, 5.41, 0.98),
            WordTiming("we", 5.45, 5.61, 0.98),
            WordTiming("can", 5.65, 6.86, 0.98),
        )
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (owner, (segment(*divergent),)),
            (right, (segment(*repeat_words(right.start)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), ["and", "then", "we", "can"])

    def test_owner_single_copy_must_span_both_corroborated_occurrences(self):
        left, owner, right = windows()
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (owner, (segment(*local_phrase(owner.start, 20.85, probability=0.98)),)),
            (right, (segment(*repeat_words(right.start)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), list(PHRASE))

    def test_collapsed_copy_crossing_segments_fails_closed(self):
        left, owner, right = windows()
        collapsed = collapsed_phrase(owner.start)
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (owner, (segment(*collapsed[:2]), segment(*collapsed[2:]))),
            (right, (segment(*repeat_words(right.start)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), list(PHRASE))

    def test_owner_repeat_is_not_tripled(self):
        left, owner, right = windows()
        chunks = [
            (left, (segment(*repeat_words(left.start)),)),
            (owner, (segment(*repeat_words(owner.start, probability=0.98)),)),
            (right, (segment(*repeat_words(right.start)),)),
        ]
        consensus = merge_chunked_transcript_segments_with_repeat_consensus(chunks)
        self.assertEqual(flat_text(consensus), list(PHRASE + PHRASE))


if __name__ == "__main__":
    unittest.main()
