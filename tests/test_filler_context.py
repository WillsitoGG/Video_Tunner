import unittest

from video_tunner.candidates import build_candidates
from video_tunner.filler_context import build_filler_assessments
from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming
from video_tunner.vad import SpeechInterval


def transcript(
    tokens: list[str],
    *,
    probabilities: list[float] | None = None,
    starts: list[float] | None = None,
    step: float = 0.32,
) -> TranscriptResult:
    words = []
    cursor = 0.1
    probabilities = probabilities or [0.99] * len(tokens)
    for index, token in enumerate(tokens):
        start = starts[index] if starts is not None else cursor
        end = start + 0.22
        words.append(WordTiming(token, start, end, probabilities[index]))
        cursor = start + step
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=" ".join(tokens),
                start=words[0].start if words else 0.0,
                end=words[-1].end if words else 0.0,
                words=tuple(words),
            ),
        ),
    )


def all_candidates(value: TranscriptResult) -> list[dict]:
    duration = max(0.5, max((word.end for segment in value.segments for word in segment.words), default=0.5))
    acoustic = build_candidates(
        value,
        [SpeechInterval(0.0, duration)],
        duration=duration,
        mode="conservative",
    )
    semantic = build_semantic_candidates(value, mode="conservative")
    counters: dict[str, int] = {}
    for item in semantic:
        kind = item["kind"]
        counters[kind] = counters.get(kind, 0) + 1
        item["id"] = f"{kind}-{counters[kind]:04d}"
        item["auto_apply"] = False
        item["decision"] = "undecided"
    combined = acoustic + semantic
    combined.sort(key=lambda item: (float(item["start"]), float(item["end"]), item["kind"]))
    return combined


def assessments(value: TranscriptResult) -> list[dict]:
    candidates = all_candidates(value)
    return build_filler_assessments(value, candidates)


class FillerContextTests(unittest.TestCase):
    def test_isolated_high_confidence_filler_is_context_only(self):
        result = assessments(transcript("vamos eh seguimos con el proyecto".split()))
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertEqual(item["status"], "isolated_hesitation")
        self.assertEqual(item["context"]["before_word"], "vamos")
        self.assertEqual(item["context"]["after_word"], "seguimos")
        self.assertFalse(item["safe_for_cut"])
        self.assertFalse(item["executable"])
        self.assertFalse(item["auto_apply"])

    def test_adjacent_fillers_are_assessed_as_cluster(self):
        result = assessments(transcript("vamos eh em seguimos".split()))
        self.assertEqual(len(result), 2)
        self.assertTrue(all(item["status"] == "hesitation_cluster" for item in result))
        self.assertTrue(all(item["safe_for_cut"] is False for item in result))

    def test_filler_inside_retake_is_protected_repair_context(self):
        value = transcript("vamos a lanzar el nuevo eh vamos a lanzar el producto mañana".split())
        candidates = all_candidates(value)
        retake = next(item for item in candidates if item["kind"] == "possible_retake")
        item = build_filler_assessments(value, candidates)[0]
        self.assertEqual(item["status"], "protected_repair_context")
        self.assertIn(retake["id"], item["repair_candidate_ids"])
        self.assertFalse(item["safe_for_cut"])

    def test_low_probability_filler_is_uncertain_asr(self):
        value = transcript(
            "vamos eh seguimos".split(),
            probabilities=[0.99, 0.30, 0.99],
        )
        item = assessments(value)[0]
        self.assertEqual(item["status"], "uncertain_asr")
        self.assertAlmostEqual(item["confidence"], 0.30, places=4)
        self.assertFalse(item["safe_for_cut"])

    def test_transcript_boundary_filler_is_boundary_hesitation(self):
        item = assessments(transcript("eh empezamos ahora".split()))[0]
        self.assertEqual(item["status"], "boundary_hesitation")
        self.assertTrue(item["context"]["at_transcript_boundary"])
        self.assertFalse(item["safe_for_cut"])

    def test_large_neighbor_gap_protects_filler_as_boundary_hesitation(self):
        value = transcript(
            ["vamos", "eh", "seguimos"],
            starts=[0.1, 1.2, 1.52],
        )
        item = assessments(value)[0]
        self.assertEqual(item["status"], "boundary_hesitation")
        self.assertGreaterEqual(item["context"]["gap_before_seconds"], 0.60)

    def test_transcript_without_filler_has_no_assessments(self):
        self.assertEqual(assessments(transcript("vamos a seguir con el proyecto".split())), [])

    def test_every_assessment_remains_non_executable(self):
        values = [
            transcript("vamos eh seguimos".split()),
            transcript("vamos eh em seguimos".split()),
            transcript("eh empezamos".split()),
            transcript("vamos a lanzar el nuevo eh vamos a lanzar el producto".split()),
        ]
        result = [item for value in values for item in assessments(value)]
        self.assertTrue(result)
        self.assertTrue(all(item["safe_for_cut"] is False for item in result))
        self.assertTrue(all(item["executable"] is False for item in result))
        self.assertTrue(all(item["auto_apply"] is False for item in result))


if __name__ == "__main__":
    unittest.main()
