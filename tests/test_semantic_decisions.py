import copy
import unittest

from video_tunner.semantic_candidates import build_semantic_candidates
from video_tunner.semantic_decisions import build_semantic_decisions
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


def semantic_candidates(value: TranscriptResult) -> list[dict]:
    items = build_semantic_candidates(value, mode="conservative")
    counters: dict[str, int] = {}
    for item in items:
        kind = item["kind"]
        counters[kind] = counters.get(kind, 0) + 1
        item["id"] = f"{kind}-{counters[kind]:04d}"
    return items


class SemanticDecisionTests(unittest.TestCase):
    def test_exact_repetition_can_only_be_a_non_executable_proposed_cut(self):
        value = transcript("vamos a lanzar vamos a lanzar el producto mañana")
        candidates = semantic_candidates(value)
        decisions = build_semantic_decisions(value, candidates)
        decision = next(item for item in decisions if item["candidate_kind"] == "possible_repetition")

        self.assertEqual(decision["decision"], "PROPOSED_CUT")
        self.assertEqual(decision["guard_status"], "pass")
        self.assertFalse(decision["executable"])
        self.assertFalse(decision["auto_apply"])
        self.assertEqual(decision["proposed_span"]["removed_text"], "vamos a lanzar")
        self.assertTrue(decision["span_validation"]["valid"])
        self.assertFalse(decision["protections"]["repeat_timing"]["compressed"])

    def test_asr_compressed_exact_repetition_fails_safe_to_review(self):
        value = transcript(
            "have a look at the have a look at the prototypes",
            step=0.12,
        )
        candidates = semantic_candidates(value)
        repeat = next(item for item in candidates if item["kind"] == "possible_repetition")
        decision = next(
            item
            for item in build_semantic_decisions(value, candidates)
            if item["candidate_id"] == repeat["id"]
        )

        self.assertLess(repeat["evidence"]["first_seconds_per_token"], 0.12)
        self.assertEqual(decision["decision"], "REVIEW")
        self.assertEqual(decision["guard_status"], "review")
        self.assertTrue(decision["protections"]["repeat_timing"]["compressed"])
        self.assertFalse(decision["executable"])
        self.assertFalse(decision["auto_apply"])

    def test_number_correction_200_to_250_is_flagged_and_kept_for_review(self):
        value = transcript("la facturación fue de 200 perdón de 250 mil euros")
        candidates = semantic_candidates(value)
        decisions = build_semantic_decisions(value, candidates)
        decision = next(item for item in decisions if item["candidate_kind"] == "explicit_correction")

        self.assertEqual(decision["decision"], "REVIEW")
        self.assertFalse(decision["executable"])
        self.assertIn("numbers", decision["protections"]["critical_changes"])
        self.assertIn("units", decision["protections"]["critical_changes"])
        self.assertIn("200", decision["protections"]["context_before"]["numbers"])
        self.assertIn("250", decision["protections"]["context_after"]["numbers"])
        self.assertIn("euros", decision["protections"]["context_after"]["units"])
        self.assertTrue(decision["protections"]["correction_relation"]["critical"])

    def test_percentage_correction_protects_number_and_unit_symbol(self):
        value = transcript("el margen era 10% perdón 15% este año")
        candidates = semantic_candidates(value)
        decisions = build_semantic_decisions(value, candidates)
        decision = next(item for item in decisions if item["candidate_kind"] == "explicit_correction")

        self.assertEqual(decision["decision"], "REVIEW")
        self.assertIn("numbers", decision["protections"]["critical_changes"])
        self.assertIn("10%", decision["protections"]["context_before"]["numbers"])
        self.assertIn("15%", decision["protections"]["context_after"]["numbers"])
        self.assertIn("%", decision["protections"]["context_before"]["units"])
        self.assertIn("%", decision["protections"]["context_after"]["units"])

    def test_negation_change_around_correction_is_protected(self):
        value = transcript("esto no funciona perdón esto funciona correctamente")
        candidates = semantic_candidates(value)
        decisions = build_semantic_decisions(value, candidates)
        decision = next(item for item in decisions if item["candidate_kind"] == "explicit_correction")

        self.assertEqual(decision["decision"], "REVIEW")
        self.assertIn("negations", decision["protections"]["critical_changes"])
        self.assertIn("no", decision["protections"]["context_before"]["negations"])

    def test_retake_with_nontrivial_intervening_content_stays_review(self):
        value = transcript("vamos a lanzar el nuevo eh vamos a lanzar el producto mañana")
        candidates = semantic_candidates(value)
        decisions = build_semantic_decisions(value, candidates)
        decision = next(item for item in decisions if item["candidate_kind"] == "possible_retake")

        self.assertEqual(decision["decision"], "REVIEW")
        self.assertFalse(decision["executable"])
        self.assertTrue(any("nuevo" in reason for reason in decision["rationale"]))

    def test_candidate_span_mismatch_fails_safe_to_keep(self):
        value = transcript("vamos a lanzar vamos a lanzar el producto")
        candidates = semantic_candidates(value)
        repeat = next(item for item in candidates if item["kind"] == "possible_repetition")
        corrupt = copy.deepcopy(repeat)
        corrupt["evidence"]["removed_text"] = "texto que no coincide"

        decision = build_semantic_decisions(value, [corrupt])[0]
        self.assertEqual(decision["decision"], "KEEP")
        self.assertEqual(decision["guard_status"], "blocked")
        self.assertFalse(decision["span_validation"]["valid"])
        self.assertFalse(decision["executable"])

    def test_all_decisions_remain_non_executable(self):
        value = transcript(
            "vamos a lanzar vamos a lanzar el producto perdón mañana"
        )
        decisions = build_semantic_decisions(value, semantic_candidates(value))
        self.assertGreaterEqual(len(decisions), 2)
        self.assertTrue(all(item["executable"] is False for item in decisions))
        self.assertTrue(all(item["auto_apply"] is False for item in decisions))


if __name__ == "__main__":
    unittest.main()
