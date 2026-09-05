from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .transcription import (
    CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    TranscriptResult,
    transcribe_audio_chunked,
)


CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS = 3.0
CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY = "deterministic_overlap_12s_3s_v1"


def transcribe_audio_chunked_12s_3s(
    audio_wav: str | Path,
    *,
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
) -> TranscriptResult:
    """Run the evidence-backed 12s/3s deterministic overlap profile.

    This remains an internal opt-in Phase 2E profile. It deliberately reuses the
    existing deterministic ownership merge without fuzzy text reconciliation.
    """
    result = transcribe_audio_chunked(
        audio_wav,
        model_name=model_name,
        language=language,
        device=device,
        compute_type=compute_type,
        window_seconds=CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
        hop_seconds=CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
    )
    return replace(result, strategy=CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY)
