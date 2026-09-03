import unittest

from video_tunner.join_safety import build_join_assessments
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming


def transcript_from_segments(segment_tokens):
    segments = []
    cursor = 0.1
    all_words = []
    for tokens in segment_tokens:
        words = []
        for token in tokens:
            word = WordTiming(token, cursor, cursor + 0.20, 0.99)
            words.append(word)
            all_words.append(word)
            cursor += 0.30
        segments.append(
            TranscriptSegment(
                text=" ".join(tokens),
                start=words[0].start,
                end=words[-1].end,
                words=tuple(words),
            )
        )
        cursor += 0.40
    return (
        TranscriptResult(
            language="es",
            language_probability=0.99,
            model="large-v3-turbo",
            device="cpu",
            compute_type="int8",
            segments=tuple(segments),
        ),
        all_words,
    )


def filler_candidate(words, index, *, candidate_id="possible_filler-0001"):
    word = words[index]
    return {
        "id": candidate_id,
        "kind": "possible_filler",
        "start": word.start,
        "end": word.end,
        "evidence": {"token": word.text, "transcription_probability": word.probability},
        "auto_apply": False,
    }


def semantic_candidate(words, start, end, kind, *, candidate_id):
    return {
        "id": candidate_id,
        "kind": kind,
        "start": words[start].start,
        "end": words[end - 1].end,
        "evidence": {
            "word_start_index": start,
            "word_end_index_exclusive": end,
            "removed_text": " ".join(word.text for word in words[start:end]),
        },
        "auto_apply": False,
    }


class JoinSafetyTests(unittest.TestCase):
    def test_pause_with_bilateral_context_is_context_only_not_safe(self):
        transcript, words = transcript_from_segments([["alpha", "beta"]])
        pause = {
            "id": "pause-0001",
            "kind": "pause",
            "start": words[0].end,
            "end": words[1].start,
            "auto_apply": False,
            "evidence": {},
        }
        result = build_join_assessments(transcript, [pause])[0]
        self.assertEqual(result["status"], "join_context_only")
        self.assertEqual(result["left_context"]["text"], "alpha")
        self.assertEqual(result["right_context"]["text"], "beta")
        self.assertFalse(result["safe_for_cut"])

    def test_strong_punctuation_is_sentence_boundary_risk(self):
        transcript, words = transcript_from_segments([["cerramos.", "continuamos"]])
        pause = {
            "id": "pause-0001",
            "kind": "pause",
            "start": words[0].end,
            "end": words[1].start,
            "auto_apply": False,
            "evidence": {},
        }
        result = build_join_assessments(transcript, [pause])[0]
        self.assertEqual(result["status"], "sentence_boundary_risk")
        self.assertTrue(result["evidence"]["punctuation_boundary"])

    def test_asr_segment_change_is_segment_boundary_risk(self):
        transcript, words = transcript_from_segments([["alpha"], ["beta"]])
        pause = {
            "id": "pause-0001",
            "kind": "pause",
            "start": words[0].end,
            "end": words[1].start,
            "auto_apply": False,
            "evidence": {},
        }
        result = build_join_assessments(transcript, [pause])[0]
        self.assertEqual(result["status"], "segment_boundary_risk")
        self.assertTrue(result["evidence"]["segment_boundary"])

    def test_negation_next_to_filler_is_critical_lexical_risk(self):
        transcript, words = transcript_from_segments([["esto", "no", "eh", "cambia"]])
        filler = filler_candidate(words, 2)
        filler_context = [
            {
                "candidate_id": filler["id"],
                "status": "isolated_hesitation",
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        ]
        result = build_join_assessments(
            transcript, [filler], filler_assessments=filler_context
        )[0]
        self.assertEqual(result["status"], "critical_lexical_context_risk")
        self.assertIn("no", result["evidence"]["critical_features_left"]["negations"])
        self.assertFalse(result["safe_for_cut"])

    def test_protected_filler_context_overrides_ordinary_join(self):
        transcript, words = transcript_from_segments([["alpha", "eh", "beta"]])
        filler = filler_candidate(words, 1)
        filler_context = [
            {
                "candidate_id": filler["id"],
                "status": "protected_repair_context",
                "repair_candidate_ids": ["possible_retake-0001"],
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        ]
        result = build_join_assessments(
            transcript, [filler], filler_assessments=filler_context
        )[0]
        self.assertEqual(result["status"], "repair_or_protected_context_risk")
        self.assertEqual(result["evidence"]["filler_context_status"], "protected_repair_context")

    def test_retake_candidate_is_repair_context_risk(self):
        transcript, words = transcript_from_segments(
            [["antes", "repite", "frase", "despues"]]
        )
        retake = semantic_candidate(
            words, 1, 3, "possible_retake", candidate_id="possible_retake-0001"
        )
        result = build_join_assessments(transcript, [retake])[0]
        self.assertEqual(result["status"], "repair_or_protected_context_risk")
        self.assertTrue(result["evidence"]["repair_kind"])

    def test_bounded_correction_uses_attempt_plus_marker_as_join_target(self):
        transcript, words = transcript_from_segments(
            [["antes", "dato", "de", "200", "perdón", "de", "250", "despues"]]
        )
        correction = semantic_candidate(
            words, 4, 5, "explicit_correction", candidate_id="explicit_correction-0001"
        )
        correction_scope = [
            {
                "id": "correction-scope-0001",
                "candidate_id": correction["id"],
                "candidate_kind": "explicit_correction",
                "status": "bounded",
                "strategy": "repeated_corrected_prefix_anchor",
                "attempt_span": {
                    "word_start_index": 2,
                    "word_end_index_exclusive": 4,
                    "start": words[2].start,
                    "end": words[3].end,
                    "text": "de 200",
                },
                "marker_span": {
                    "word_start_index": 4,
                    "word_end_index_exclusive": 5,
                    "start": words[4].start,
                    "end": words[4].end,
                    "text": "perdón",
                },
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        ]
        result = build_join_assessments(
            transcript, [correction], correction_scopes=correction_scope
        )[0]
        self.assertEqual(result["status"], "repair_or_protected_context_risk")
        self.assertEqual(
            result["target_span"]["source"], "bounded_correction_attempt_plus_marker"
        )
        self.assertEqual(result["target_span"]["text"], "de 200 perdón")
        self.assertEqual(result["left_context"]["text"], "dato")
        self.assertEqual(result["right_context"]["text"], "de")

    def test_ambiguous_correction_has_no_join_target(self):
        transcript, words = transcript_from_segments(
            [["antes", "idea", "perdón", "otra", "cosa"]]
        )
        correction = semantic_candidate(
            words, 2, 3, "explicit_correction", candidate_id="explicit_correction-0001"
        )
        scopes = [
            {
                "candidate_id": correction["id"],
                "status": "ambiguous",
                "attempt_span": None,
                "marker_span": {
                    "word_start_index": 2,
                    "word_end_index_exclusive": 3,
                    "text": "perdón",
                },
            }
        ]
        result = build_join_assessments(
            transcript, [correction], correction_scopes=scopes
        )[0]
        self.assertEqual(result["status"], "invalid_or_unbounded_target")
        self.assertIsNone(result["target_span"])

    def test_mismatched_semantic_span_fails_safe(self):
        transcript, words = transcript_from_segments(
            [["antes", "repite", "frase", "despues"]]
        )
        candidate = semantic_candidate(
            words, 1, 3, "possible_repetition", candidate_id="possible_repetition-0001"
        )
        candidate["evidence"]["removed_text"] = "texto distinto"
        result = build_join_assessments(transcript, [candidate])[0]
        self.assertEqual(result["status"], "invalid_or_unbounded_target")
        self.assertFalse(result["evidence"]["target_resolved"])

    def test_filler_at_transcript_edge_is_protected(self):
        transcript, words = transcript_from_segments([["eh", "alpha", "beta"]])
        filler = filler_candidate(words, 0)
        result = build_join_assessments(transcript, [filler])[0]
        self.assertEqual(result["status"], "transcript_edge")
        self.assertIsNone(result["left_context"])
        self.assertIsNotNone(result["right_context"])

    def test_every_join_assessment_is_non_executable(self):
        transcript, words = transcript_from_segments([["alpha", "eh", "beta"]])
        filler = filler_candidate(words, 1)
        results = build_join_assessments(transcript, [filler])
        self.assertTrue(results)
        for item in results:
            self.assertFalse(item["safe_for_cut"])
            self.assertFalse(item["executable"])
            self.assertFalse(item["auto_apply"])


if __name__ == "__main__":
    unittest.main()
