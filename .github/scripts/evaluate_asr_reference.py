from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import unicodedata
from pathlib import Path


def normalize_words(text: str) -> list[str]:
    value = unicodedata.normalize("NFKD", text.lower())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return value.split()


def levenshtein(reference: list[str], hypothesis: list[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for i, ref_word in enumerate(reference, start=1):
        current = [i]
        for j, hyp_word in enumerate(hypothesis, start=1):
            substitution = previous[j - 1] + (ref_word != hyp_word)
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            current.append(min(substitution, insertion, deletion))
        previous = current
    return previous[-1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript_json")
    parser.add_argument("reference_txt")
    parser.add_argument("--timeline-duration", type=float, required=True)
    parser.add_argument("--max-wer", type=float, default=0.15)
    parser.add_argument("--min-word-ratio", type=float, default=0.80)
    args = parser.parse_args()

    transcript = json.loads(Path(args.transcript_json).read_text(encoding="utf-8"))
    reference_text = Path(args.reference_txt).read_text(encoding="utf-8")
    reference_words = normalize_words(reference_text)

    timed_words: list[tuple[str, float, float]] = []
    for segment in transcript.get("segments", []):
        for word in segment.get("words", []):
            text = str(word.get("text", "")).strip()
            start = float(word.get("start"))
            end = float(word.get("end"))
            timed_words.append((text, start, end))

    hypothesis_words = normalize_words(" ".join(text for text, _, _ in timed_words))
    distance = levenshtein(reference_words, hypothesis_words)
    wer = distance / max(1, len(reference_words))
    ratio = len(hypothesis_words) / max(1, len(reference_words))

    timestamps_finite = all(math.isfinite(start) and math.isfinite(end) for _, start, end in timed_words)
    timestamps_nonnegative = all(start >= -1e-6 and end >= -1e-6 for _, start, end in timed_words)
    timestamps_ordered = all(start <= end + 1e-6 for _, start, end in timed_words)
    starts_monotonic = all(
        timed_words[index][1] + 1e-6 >= timed_words[index - 1][1]
        for index in range(1, len(timed_words))
    )
    timestamps_in_timeline = all(end <= args.timeline_duration + 0.5 for _, _, end in timed_words)
    durations = [end - start for _, start, end in timed_words if end >= start]
    median_word_duration = statistics.median(durations) if durations else 0.0
    median_duration_sane = 0.0 < median_word_duration < 1.5

    checks = {
        "wer_pass": wer <= args.max_wer,
        "word_ratio_pass": ratio >= args.min_word_ratio,
        "timestamps_finite": timestamps_finite,
        "timestamps_nonnegative": timestamps_nonnegative,
        "timestamps_start_le_end": timestamps_ordered,
        "timestamps_start_monotonic": starts_monotonic,
        "timestamps_in_timeline": timestamps_in_timeline,
        "median_word_duration_sane": median_duration_sane,
    }
    result = {
        "reference_word_count": len(reference_words),
        "hypothesis_word_count": len(hypothesis_words),
        "word_count_ratio": round(ratio, 6),
        "levenshtein_word_errors": distance,
        "wer": round(wer, 6),
        "median_word_duration_seconds": round(median_word_duration, 6),
        "timeline_duration_seconds": args.timeline_duration,
        "thresholds": {
            "max_wer": args.max_wer,
            "min_word_ratio": args.min_word_ratio,
        },
        "checks": checks,
        "pass": all(checks.values()),
        "normalized_reference": " ".join(reference_words),
        "normalized_hypothesis": " ".join(hypothesis_words),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
