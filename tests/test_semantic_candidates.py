import unittest

from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming


def transcript_from_words(items: list[tuple[str, float, float]]) -> TranscriptResult:
    words = tuple(WordTiming(text, start, end, 0.99) for text, start, end in items)
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=" ".join(item[0] for item in items),
                start=items[0][1] if items else 0.0,
                end=items[-1][2] if items else 0.0,
                words=words,
            ),
        ),
    )


def timed(text: str, *, step: float = 0.32, start: float = 0.0) -> list[tuple[str, float, float]]:
    result = []
    cursor = start
    for token in text.split():
        result.append((token, cursor, cursor + step * 0.75))
        cursor += step
    return result


class SemanticCandidateTests(unittest.TestCase):
    def test_adjacent_phrase_repetition_keeps_later_occurrence_outside_span(self):
        transcript = transcript_from_words(timed("vamos a lanzar vamos a lanzar el producto mañana"))
        candidates = build_semantic_candidates(transcript, mode="conservative")
        repeat = next(item for item in candidates if item["kind"] == "possible_repetition")

        self.assertEqual(repeat["evidence"]["removed_text"], "vamos a lanzar")
        self.assertEqual(repeat["evidence"]["second_occurrence_text"], "vamos a lanzar")
        self.assertEqual(repeat["evidence"]["keep_occurrence"], "later")
        self.assertGreater(repeat["evidence"]["first_seconds_per_token"], 0.12)
        self.assertGreater(repeat["evidence"]["second_seconds_per_token"], 0.12)
        self.assertEqual(repeat["suggested_decision"], "REVIEW")
        self.assertFalse(repeat["auto_apply"])

    def test_repeated_opener_with_intervening_fumble_is_possible_retake(self):
        transcript = transcript_from_words(
            timed("vamos a lanzar el nuevo eh vamos a lanzar el producto mañana")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        retake = next(item for item in candidates if item["kind"] == "possible_retake")

        self.assertEqual(retake["evidence"]["repeated_opener_text"], "vamos a lanzar el")
        self.assertEqual(retake["evidence"]["intervening_text"], "nuevo eh")
        self.assertEqual(retake["evidence"]["removed_text"], "vamos a lanzar el nuevo eh")
        self.assertEqual(retake["evidence"]["second_occurrence_text"], "vamos a lanzar el")
        self.assertTrue(retake["evidence"]["repair_evidence"])
        self.assertFalse(retake["auto_apply"])

    def test_explicit_span_marker_does_not_guess_the_wrong_take_boundary(self):
        transcript = transcript_from_words(
            timed("la facturación fue de 200 perdón de 250 mil euros")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        correction = next(item for item in candidates if item["kind"] == "explicit_correction")

        self.assertEqual(correction["evidence"]["removed_text"], "perdón")
        self.assertEqual(correction["evidence"]["span_scope"], "marker_only")
        self.assertIn("200", correction["evidence"]["context_before"])
        self.assertIn("250", correction["evidence"]["context_after"])
        self.assertTrue(correction["evidence"]["requires_semantic_review"])
        self.assertFalse(correction["evidence"]["span_safe_for_auto_apply"])

    def test_legitimate_reuse_far_apart_is_not_a_retake(self):
        first = timed("pulsa el botón guardar", start=0.0)
        second = timed("ahora revisamos otra pantalla", start=4.0)
        third = timed("pulsa el botón guardar", start=20.0)
        transcript = transcript_from_words(first + second + third)
        candidates = build_semantic_candidates(transcript, mode="conservative")

        semantic = [item for item in candidates if item["kind"] in {"possible_repetition", "possible_retake"}]
        self.assertEqual(semantic, [])

    def test_conservative_mode_rejects_nearby_legitimate_reuse_with_continuation_markers(self):
        transcript = transcript_from_words(
            timed("vamos a lanzar el producto ahora y luego vamos a lanzar una campaña distinta")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        self.assertFalse(any(item["kind"] == "possible_retake" for item in candidates))

    def test_ambiguous_correction_marker_is_not_flagged_when_used_literally(self):
        for text in (
            "quiero decir algo importante sobre el proyecto",
            "lo que quiero decir es que necesitamos tiempo",
        ):
            with self.subTest(text=text):
                transcript = transcript_from_words(timed(text))
                candidates = build_semantic_candidates(transcript, mode="conservative")
                self.assertFalse(any(item["kind"] == "explicit_correction" for item in candidates))

    def test_ambiguous_correction_marker_still_works_for_numeric_replacement(self):
        transcript = transcript_from_words(timed("son veinte quiero decir treinta unidades"))
        candidates = build_semantic_candidates(transcript, mode="conservative")
        correction = next(item for item in candidates if item["kind"] == "explicit_correction")
        self.assertEqual(correction["evidence"]["removed_text"], "quiero decir")
        self.assertTrue(correction["evidence"]["numeric_replacement_cue"])

    def test_i_mean_discourse_without_repair_evidence_is_rejected_conservatively(self):
        transcript = transcript_from_words(
            timed("we chose a fashion item i mean it is just a minor detailed point")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        self.assertFalse(any(item["kind"] == "explicit_correction" for item in candidates))

    def test_i_mean_after_explicit_dash_is_review_candidate(self):
        transcript = transcript_from_words(
            timed("i just wondered - i mean h- how will people put these down")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        correction = next(item for item in candidates if item["kind"] == "explicit_correction")
        self.assertEqual(correction["evidence"]["removed_text"], "i mean")
        self.assertTrue(correction["evidence"]["repair_boundary_before"])
        self.assertFalse(correction["auto_apply"])

    def test_i_mean_question_reframe_survives_asr_punctuation_loss(self):
        transcript = transcript_from_words(
            timed("yeah yeah i mean it is a detailed point i just wonder i mean how will people put these down")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        corrections = [item for item in candidates if item["kind"] == "explicit_correction"]

        self.assertEqual(len(corrections), 1)
        self.assertEqual(corrections[0]["evidence"]["removed_text"], "i mean")
        self.assertTrue(corrections[0]["evidence"]["question_reframe_cue"])
        self.assertFalse(corrections[0]["evidence"]["repair_boundary_before"])
        self.assertFalse(corrections[0]["evidence"]["numeric_replacement_cue"])
        self.assertFalse(corrections[0]["auto_apply"])

    def test_perdon_followed_by_hesitation_without_boundary_is_rejected_conservatively(self):
        transcript = transcript_from_words(
            timed("ahora se me está bloqueando perdón eh que muchas gracias")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        self.assertFalse(any(item["kind"] == "explicit_correction" for item in candidates))

    def test_perdon_after_fragment_is_review_candidate(self):
        transcript = transcript_from_words(timed("pero la dee- perdón la de Marta ya está pasada"))
        candidates = build_semantic_candidates(transcript, mode="conservative")
        correction = next(item for item in candidates if item["kind"] == "explicit_correction")
        self.assertEqual(correction["evidence"]["removed_text"], "perdón")
        self.assertTrue(correction["evidence"]["repair_boundary_before"])
        self.assertFalse(correction["auto_apply"])

    def test_conservative_mode_does_not_flag_two_word_emphasis(self):
        transcript = transcript_from_words(timed("muy bien muy bien seguimos"))
        candidates = build_semantic_candidates(transcript, mode="conservative")
        self.assertFalse(any(item["kind"] == "possible_repetition" for item in candidates))

    def test_every_semantic_candidate_is_review_only(self):
        transcript = transcript_from_words(
            timed("vamos a lanzar vamos a lanzar perdón el producto")
        )
        candidates = build_semantic_candidates(transcript, mode="conservative")
        self.assertGreaterEqual(len(candidates), 2)
        self.assertTrue(all(item["decision"] == "undecided" for item in candidates))
        self.assertTrue(all(item["suggested_decision"] == "REVIEW" for item in candidates))
        self.assertTrue(all(item["auto_apply"] is False for item in candidates))


if __name__ == "__main__":
    unittest.main()
