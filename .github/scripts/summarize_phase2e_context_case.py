from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def normalize_phrase(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    asciiish = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    tokens = [re.sub(r"[^a-z0-9]+", "", raw) for raw in asciiish.split()]
    return " ".join(token for token in tokens if token)


def one(items: list[dict], *, key: str, value: str) -> dict | None:
    matches = [item for item in items if str(item.get(key) or "") == value]
    if len(matches) > 1:
        raise ValueError(f"Multiple records for {key}={value}: {len(matches)}")
    return matches[0] if matches else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis")
    parser.add_argument("--expected-text", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    analysis = json.loads(Path(args.analysis).read_text(encoding="utf-8-sig"))
    expected = normalize_phrase(args.expected_text)
    candidates = list(analysis.get("candidates") or [])
    repetitions = [item for item in candidates if item.get("kind") == "possible_repetition"]
    text_matches = [
        item
        for item in repetitions
        if normalize_phrase(str((item.get("evidence") or {}).get("removed_text") or "")) == expected
    ]
    if len(text_matches) != 1:
        result = {
            "case_id": args.case_id,
            "expected_text": args.expected_text,
            "matched_candidate": None,
            "repeat_candidate_count": len(repetitions),
            "exact_text_match_count": len(text_matches),
            "classification": "candidate_missing_or_ambiguous",
        }
    else:
        candidate = text_matches[0]
        candidate_id = str(candidate.get("id") or "")
        semantic = one(list(analysis.get("semantic_decisions") or []), key="candidate_id", value=candidate_id)
        join = one(list(analysis.get("join_assessments") or []), key="candidate_id", value=candidate_id)
        eligibility = one(list(analysis.get("eligibility_assessments") or []), key="candidate_id", value=candidate_id)
        promotion = one(list(analysis.get("promotion_assessments") or []), key="candidate_id", value=candidate_id)
        acoustic = None
        if join is not None:
            acoustic = one(
                list(analysis.get("acoustic_join_assessments") or []),
                key="join_assessment_id",
                value=str(join.get("id") or ""),
            )

        promotion_status = None if promotion is None else promotion.get("status")
        eligibility_status = None if eligibility is None else eligibility.get("status")
        if promotion_status == "eligible_for_promotion_review":
            classification = "promotion_eligible"
        elif eligibility_status == "blocked_join_context":
            classification = "context_blocked_at_join"
        elif eligibility_status == "blocked_acoustic_context":
            classification = "context_blocked_at_acoustic"
        elif eligibility_status == "invalid_removed_text":
            classification = "removed_text_invalid"
        else:
            classification = "blocked_other"

        result = {
            "case_id": args.case_id,
            "expected_text": args.expected_text,
            "matched_candidate": {
                "id": candidate_id,
                "kind": candidate.get("kind"),
                "start": candidate.get("start"),
                "end": candidate.get("end"),
                "removed_text": (candidate.get("evidence") or {}).get("removed_text"),
                "word_start_index": (candidate.get("evidence") or {}).get("word_start_index"),
                "word_end_index_exclusive": (candidate.get("evidence") or {}).get("word_end_index_exclusive"),
            },
            "semantic": None if semantic is None else {
                "decision": semantic.get("decision"),
                "guard_status": semantic.get("guard_status"),
            },
            "join": None if join is None else {
                "id": join.get("id"),
                "status": join.get("status"),
                "left_context": join.get("left_context"),
                "right_context": join.get("right_context"),
                "evidence": join.get("evidence"),
            },
            "acoustic": None if acoustic is None else {
                "status": acoustic.get("status"),
                "measurement_available": acoustic.get("measurement_available"),
                "metrics": acoustic.get("metrics"),
            },
            "eligibility": None if eligibility is None else {
                "status": eligibility.get("status"),
                "blockers": eligibility.get("blockers"),
                "future_promotion_candidate": eligibility.get("future_promotion_candidate"),
                "removed_text_validation": eligibility.get("removed_text_validation"),
            },
            "promotion": None if promotion is None else {
                "status": promotion.get("status"),
                "blockers": promotion.get("blockers"),
                "promotion_review_candidate": promotion.get("promotion_review_candidate"),
            },
            "classification": classification,
        }

    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
