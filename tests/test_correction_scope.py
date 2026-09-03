import unittest

from video_tunner.correction_scope import build_correction_scopes
from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming


def transcript(text: str, *, step: float = 0.32) -> TranscriptResult:
    words = []
    cursor = 0.1
    for token in text.split():
        words.append(WordTiming(token, cursor, cursor + step * 0.72, 0.99))
        cursor += step
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=text,
                start=words[0].start if words else 0.0,
                end=words[-1].end if words else 0.0,
                words=tuple(words),
            ),
        ),
    )


def correction_scopes(text: str) -> list[dict]:
    value = transcript(text)
    candidates = build_semantic_candidates(value, mode="conservative")
    counters: dict[str, int] = {}
    for candidate in candidates:
        kind = candidate["kind"]
        counters[kind] = counters.get(kind, 0) + 1
        candidate["id"] = f"{kind}-{counters[kind]:04d}"
    return build_correction_scopes(value, candidates)


class CorrectionScopeTests(unittest.TestCase):
    def test_repeated_corrected_prefix_bounds_numeric_attempt_without_authorizing_cut(self):
        scopes = correction_scopes("la facturación fue de 200 perdón de 250 mil euros")
        self.assertEqual(len(scopes), 1)
        scope = scopes[0]
        self.assertEqual(scope["status"], "bounded")
        self.assertEqual(scope["strategy"], "repeated_corrected_prefix_anchor")
        self.assertEqual(scope["attempt_span"]["text"], "de 200")
        self.assertEqual(scope["marker_span"]["text"], "perdón")
        self.assertFalse(scope["safe_for_cut"])
        self.assertFalse(scope["executable"])
        self.assertFalse(scope["auto_apply"])

    def test_local_numeric_replacement_bounds_only_wrong_value(self):
        scope = correction_scopes("el margen era 10% perdón 15% este año")[0]
        self.assertEqual(scope["status"], "bounded")
        self.assertEqual(scope["strategy"], "local_numeric_replacement")
        self.assertEqual(scope["attempt_span"]["text"], "10%")
        self.assertFalse(scope["safe_for_cut"])

    def test_repeated_subject_anchor_can_bound_negated_attempt(self):
        scope = correction_scopes("esto no funciona perdón esto funciona correctamente")[0]
        self.assertEqual(scope["status"], "bounded")
        self.assertEqual(scope["strategy"], "repeated_corrected_prefix_anchor")
        self.assertEqual(scope["attempt_span"]["text"], "esto no funciona")
        self.assertFalse(scope["executable"])

    def test_realistic_i_mean_question_reframe_remains_ambiguous_scope(self):
        scope = correction_scopes("i just wonder i mean how will people put these down i wonder")[0]
        self.assertEqual(scope["status"], "ambiguous")
        self.assertEqual(scope["strategy"], "no_deterministic_left_boundary")
        self.assertIsNone(scope["attempt_span"])
        self.assertEqual(scope["marker_span"]["text"], "i mean")
        self.assertFalse(scope["safe_for_cut"])
        self.assertFalse(scope["auto_apply"])

    def test_repeated_phrase_can_bound_entity_replacement_but_still_review_only(self):
        scope = correction_scopes("we chose Marta sorry we chose Maria for the demo")[0]
        self.assertEqual(scope["status"], "bounded")
        self.assertEqual(scope["attempt_span"]["text"], "we chose Marta")
        self.assertFalse(scope["safe_for_cut"])
        self.assertFalse(scope["executable"])

    def test_non_correction_candidates_do_not_create_scope_records(self):
        self.assertEqual(correction_scopes("vamos a lanzar vamos a lanzar el producto"), [])

    def test_every_scope_is_non_executable_and_non_auto_apply(self):
        examples = (
            "la facturación fue de 200 perdón de 250 mil euros",
            "el margen era 10% perdón 15% este año",
            "esto no funciona perdón esto funciona correctamente",
            "i just wonder i mean how will people put these down i wonder",
        )
        scopes = [scope for text in examples for scope in correction_scopes(text)]
        self.assertTrue(scopes)
        self.assertTrue(all(scope["safe_for_cut"] is False for scope in scopes))
        self.assertTrue(all(scope["executable"] is False for scope in scopes))
        self.assertTrue(all(scope["auto_apply"] is False for scope in scopes))


if __name__ == "__main__":
    unittest.main()
