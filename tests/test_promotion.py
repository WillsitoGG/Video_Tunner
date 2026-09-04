import unittest

from video_tunner.promotion import build_promotion_assessments


def candidate(candidate_id: str, kind: str = "possible_repetition") -> dict:
    return {
        "id": candidate_id,
        "kind": kind,
        "start": 1.0,
        "end": 2.0,
        "auto_apply": False,
    }


def eligibility(
    candidate_id: str,
    *,
    kind: str = "possible_repetition",
    status: str = "foundation_guards_pass",
    future: bool = True,
    removed_valid: bool = True,
) -> dict:
    return {
        "id": f"eligibility-{candidate_id}",
        "candidate_id": candidate_id,
        "candidate_kind": kind,
        "status": status,
        "future_promotion_candidate": future,
        "removed_text_validation": {
            "valid": removed_valid,
            "source": "candidate_word_span",
            "text": "vamos a lanzar",
            "start": 1.0,
            "end": 2.0,
            "word_start_index": 3,
            "word_end_index_exclusive": 6,
        },
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


class PromotionPolicyTests(unittest.TestCase):
    def test_exact_repetition_foundation_pass_is_review_candidate_not_edit(self):
        assessments = build_promotion_assessments(
            [candidate("c1")],
            [eligibility("c1")],
            mode="conservative",
        )
        self.assertEqual(len(assessments), 1)
        item = assessments[0]
        self.assertEqual(item["status"], "eligible_for_promotion_review")
        self.assertTrue(item["promotion_review_candidate"])
        self.assertTrue(item["requires_explicit_approval"])
        self.assertEqual(item["approval_state"], "required")
        self.assertFalse(item["approved"])
        self.assertIsNone(item["edit"])
        self.assertEqual(item["target_preview"]["text"], "vamos a lanzar")
        self.assertFalse(item["safe_for_cut"])
        self.assertFalse(item["executable"])
        self.assertFalse(item["auto_apply"])

    def test_upstream_blocker_can_never_be_rescued_by_promotion(self):
        item = build_promotion_assessments(
            [candidate("c1")],
            [
                eligibility(
                    "c1",
                    status="blocked_join_context",
                    future=False,
                )
            ],
            mode="conservative",
        )[0]
        self.assertEqual(item["status"], "blocked_upstream_eligibility")
        self.assertIn("blocked_join_context", item["blockers"])
        self.assertFalse(item["promotion_review_candidate"])
        self.assertIsNone(item["target_preview"])
        self.assertIsNone(item["edit"])

    def test_foundation_pause_is_blocked_without_human_positive_class_evidence(self):
        item = build_promotion_assessments(
            [candidate("c1", "pause")],
            [eligibility("c1", kind="pause")],
            mode="conservative",
        )[0]
        self.assertEqual(item["status"], "blocked_unvalidated_candidate_kind")
        self.assertIn(
            "candidate_kind_lacks_human_positive_closeout_evidence",
            item["blockers"],
        )
        self.assertFalse(item["promotion_review_candidate"])
        self.assertFalse(item["approved"])
        self.assertIsNone(item["edit"])

    def test_aggressive_mode_does_not_broaden_candidate_classes_yet(self):
        item = build_promotion_assessments(
            [candidate("c1", "possible_filler")],
            [eligibility("c1", kind="possible_filler")],
            mode="aggressive",
        )[0]
        self.assertEqual(item["status"], "blocked_unvalidated_candidate_kind")
        self.assertFalse(item["promotion_review_candidate"])

    def test_invalid_candidate_reference_fails_safe(self):
        item = build_promotion_assessments(
            [],
            [eligibility("missing")],
            mode="conservative",
        )[0]
        self.assertEqual(item["status"], "invalid_candidate_reference")
        self.assertFalse(item["promotion_review_candidate"])
        self.assertIsNone(item["edit"])

    def test_kind_mismatch_fails_safe(self):
        item = build_promotion_assessments(
            [candidate("c1", "possible_repetition")],
            [eligibility("c1", kind="pause")],
            mode="conservative",
        )[0]
        self.assertEqual(item["status"], "invalid_candidate_reference")
        self.assertIn("candidate_kind_mismatch", item["blockers"])

    def test_invalid_removed_text_cannot_be_promoted_even_if_status_is_inconsistent(self):
        item = build_promotion_assessments(
            [candidate("c1")],
            [eligibility("c1", removed_valid=False)],
            mode="conservative",
        )[0]
        self.assertEqual(item["status"], "blocked_removed_text_validation")
        self.assertFalse(item["promotion_review_candidate"])
        self.assertIsNone(item["target_preview"])

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            build_promotion_assessments(
                [candidate("c1")],
                [eligibility("c1")],
                mode="unknown",
            )


if __name__ == "__main__":
    unittest.main()
