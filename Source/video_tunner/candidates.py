from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .transcription import TranscriptResult, WordTiming
from .vad import SpeechInterval, non_speech_gaps

CANDIDATE_SETTINGS = {
    "conservative": {
        "min_vad_gap": 0.65,
        "min_word_gap": 0.45,
    },
    "aggressive": {
        "min_vad_gap": 0.35,
        "min_word_gap": 0.25,
    },
}

# Only unmistakable vocal hesitation tokens. Ambiguous discourse words are left
# for the future semantic classifier.
OBVIOUS_FILLERS = {
    "eh", "em", "erm", "er", "um", "umm", "uh", "uhh", "mmm", "mm", "hmm"
}


def sha256_file(source: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(source).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _all_words(transcript: TranscriptResult) -> list[WordTiming]:
    words = [word for segment in transcript.segments for word in segment.words]
    return sorted(words, key=lambda word: (word.start, word.end))


def _context_for_gap(words: list[WordTiming], start: float, end: float) -> dict[str, Any]:
    before = None
    after = None
    for word in words:
        if word.end <= start + 1e-6:
            before = word
            continue
        if word.start >= end - 1e-6:
            after = word
            break
    return {
        "before_word": None if before is None else before.text,
        "after_word": None if after is None else after.text,
    }


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def build_candidates(
    transcript: TranscriptResult,
    speech_intervals: list[SpeechInterval],
    *,
    duration: float,
    mode: str,
) -> list[dict[str, Any]]:
    if mode not in CANDIDATE_SETTINGS:
        raise ValueError(f"Modo desconocido: {mode}")
    settings = CANDIDATE_SETTINGS[mode]
    words = _all_words(transcript)
    candidates: list[dict[str, Any]] = []

    # 1) Acoustic non-speech gaps from Silero VAD.
    for start, end in non_speech_gaps(
        speech_intervals,
        duration=duration,
        min_duration=float(settings["min_vad_gap"]),
    ):
        candidates.append(
            {
                "id": "",
                "kind": "pause",
                "start": round(start, 6),
                "end": round(end, 6),
                "duration": round(end - start, 6),
                "reason": "Tramo sin habla detectado por Silero VAD",
                "confidence": None,
                "decision": "undecided",
                "auto_apply": False,
                "evidence": {
                    "silero_vad": True,
                    "word_gap": False,
                    **_context_for_gap(words, start, end),
                },
            }
        )

    # 2) Word-aligned gaps. Enrich an overlapping VAD candidate when possible;
    # otherwise retain a separate candidate for future semantic classification.
    for previous, current in zip(words, words[1:]):
        start = previous.end
        end = current.start
        gap = end - start
        if gap < float(settings["min_word_gap"]):
            continue
        matched = None
        for candidate in candidates:
            overlap = _overlap(start, end, float(candidate["start"]), float(candidate["end"]))
            if overlap >= min(gap, float(candidate["duration"])) * 0.5:
                matched = candidate
                break
        if matched is not None:
            matched["evidence"]["word_gap"] = True
            matched["evidence"]["before_word"] = previous.text
            matched["evidence"]["after_word"] = current.text
        else:
            candidates.append(
                {
                    "id": "",
                    "kind": "pause",
                    "start": round(start, 6),
                    "end": round(end, 6),
                    "duration": round(gap, 6),
                    "reason": "Pausa entre palabras detectada por timestamps de Whisper",
                    "confidence": None,
                    "decision": "undecided",
                    "auto_apply": False,
                    "evidence": {
                        "silero_vad": False,
                        "word_gap": True,
                        "before_word": previous.text,
                        "after_word": current.text,
                    },
                }
            )

    # 3) Obvious filler tokens. They remain review-only until semantic protection exists.
    for word in words:
        normalised = word.text.lower().strip(".,!?;:\"'()[]{}—-…")
        if normalised not in OBVIOUS_FILLERS:
            continue
        candidates.append(
            {
                "id": "",
                "kind": "possible_filler",
                "start": round(word.start, 6),
                "end": round(word.end, 6),
                "duration": round(max(0.0, word.end - word.start), 6),
                "reason": f"Muletilla vocal candidata: {word.text}",
                "confidence": None,
                "decision": "undecided",
                "auto_apply": False,
                "evidence": {
                    "token": word.text,
                    "transcription_probability": word.probability,
                },
            }
        )

    candidates.sort(key=lambda item: (float(item["start"]), float(item["end"]), item["kind"]))
    counters: Counter[str] = Counter()
    for candidate in candidates:
        counters[candidate["kind"]] += 1
        candidate["id"] = f"{candidate['kind']}-{counters[candidate['kind']]:04d}"
    return candidates


def build_analysis_report(
    source: str | Path,
    probe: dict[str, Any],
    transcript: TranscriptResult,
    speech_intervals: list[SpeechInterval],
    *,
    mode: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = Counter(candidate["kind"] for candidate in candidates)
    return {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "file": Path(source).name,
            "duration_seconds": probe["duration_seconds"],
            "sha256": sha256_file(source),
        },
        "mode": mode,
        "engines": {
            "transcription": {
                "name": "faster-whisper",
                "model": transcript.model,
                "device": transcript.device,
                "compute_type": transcript.compute_type,
            },
            "voice_activity_detection": {
                "name": "silero-vad",
            },
        },
        "transcript": {
            "language": transcript.language,
            "language_probability": transcript.language_probability,
            "segment_count": len(transcript.segments),
            "word_count": transcript.word_count,
        },
        "speech_segments": [
            {"start": round(item.start, 6), "end": round(item.end, 6)}
            for item in speech_intervals
        ],
        "candidates": candidates,
        "summary": {
            "candidate_count": len(candidates),
            "candidate_kinds": dict(sorted(counts.items())),
            "automatic_edits": 0,
            "review_required": len(candidates),
        },
        "safety": {
            "candidates_are_not_edits": True,
            "semantic_protection_enabled": False,
            "note": "Ningún candidato de esta fase se aplica automáticamente.",
        },
    }


def save_analysis_report(report: dict[str, Any], destination: str | Path) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
