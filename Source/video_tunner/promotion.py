from __future__ import annotations

from typing import Any


PROMOTION_SETTINGS = {
    "conservative": {
        "evidence_backed_kinds": frozenset({"possible_repetition"}),
        "requires_explicit_approval": True,
    },
    "aggressive": {
        # Phase 2E.1 deliberately does not broaden classes by mode. Human-positive
        # evidence currently supports exact repetitions only.
        "evidence_backed_kinds": frozenset({"possible_repetition"}),
        "requires_explicit_approval": True,
    },
}

PROMOTION_REVIEW_STATUS = "eligible_for_promotion_review"


def _target_preview(eligibility: dict[str, Any]) -> dict[str, Any] | None:
    removed = eligibility.get("removed_text_validation")
    if not isinstance(removed, dict) or not removed.get("valid"):
        return None
    return {
        "source": removed.get("source"),
        "text": removed.get("text"),
        "start": removed.get("start"),
        "end": removed.get("end"),
        "word_start_index": removed.get("word_start_index"),
        "word_end_index_exclusive": removed.get("word_end_index_exclusive"),
    }


def _record(
    *,
    index: int,
    candidate: dict[str, Any] | None,
    eligibility: dict[str, Any],
    mode: str,
    status: str,
    blockers: list[str],
) -> dict[str, Any]:
    candidate_id = eligibility.get("candidate_id")
    candidate_kind = (
        candidate.get("kind") if isinstance(candidate, dict) else eligibility.get("candidate_kind")
    )
    review_candidate = status == PROMOTION_REVIEW_STATUS
    return {
        "id": f"promotion-assessment-{index:04d}",
        "eligibility_assessment_id": eligibility.get("id"),
        "candidate_id": candidate_id,
        "candidate_kind": candidate_kind,
        "mode": mode,
        "status": status,
        "blockers": blockers,
        "promotion_review_candidate": review_candidate,
        "requires_explicit_approval": True,
        "approval_state": "required" if review_candidate else "not_applicable",
        "approved": False,
        "target_preview": _target_preview(eligibility) if review_candidate else None,
        "edit": None,
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def build_promotion_assessments(
    candidates: list[dict[str, Any]],
    eligibility_assessments: list[dict[str, Any]],
    *,
    mode: str,
) -> list[dict[str, Any]]:
    """Assess eligibility records for *reviewable* promotion, never for execution.

    Phase 2E.1 introduces a policy boundary between combined eligibility and a
    future approved Edit Plan. A record can become a promotion-review candidate
    only when all 2D foundation guards passed *and* its candidate kind has direct
    human-positive removability evidence. Even then, the record remains
    unapproved, non-executable and contains no edit.
    """
    if mode not in PROMOTION_SETTINGS:
        raise ValueError(f"Modo desconocido: {mode}")

    settings = PROMOTION_SETTINGS[mode]
    evidenced_kinds = settings["evidence_backed_kinds"]
    candidate_by_id = {
        str(candidate.get("id")): candidate
        for candidate in candidates
        if candidate.get("id")
    }

    results: list[dict[str, Any]] = []
    for index, eligibility in enumerate(eligibility_assessments, start=1):
        candidate_id = str(eligibility.get("candidate_id") or "")
        candidate = candidate_by_id.get(candidate_id)
        blockers: list[str] = []

        if candidate is None:
            status = "invalid_candidate_reference"
            blockers.append("candidate_not_found")
        elif str(candidate.get("kind") or "") != str(eligibility.get("candidate_kind") or ""):
            status = "invalid_candidate_reference"
            blockers.append("candidate_kind_mismatch")
        elif (
            eligibility.get("status") != "foundation_guards_pass"
            or not eligibility.get("future_promotion_candidate")
        ):
            status = "blocked_upstream_eligibility"
            blockers.append(str(eligibility.get("status") or "eligibility_not_passed"))
        elif not bool((eligibility.get("removed_text_validation") or {}).get("valid")):
            status = "blocked_removed_text_validation"
            blockers.append("removed_text_not_valid")
        elif str(candidate.get("kind") or "") not in evidenced_kinds:
            status = "blocked_unvalidated_candidate_kind"
            blockers.append("candidate_kind_lacks_human_positive_closeout_evidence")
        else:
            status = PROMOTION_REVIEW_STATUS

        results.append(
            _record(
                index=index,
                candidate=candidate,
                eligibility=eligibility,
                mode=mode,
                status=status,
                blockers=blockers,
            )
        )

    return results
