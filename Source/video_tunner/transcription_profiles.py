from __future__ import annotations

from pathlib import Path

from .transcription import (
    CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
    TranscriptResult,
)
from .transcription_consensus import transcribe_audio_chunked_with_repeat_consensus


CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS = 3.0
CHUNKED_TRANSCRIPTION_12S_3S_OWNERSHIP_STRATEGY = "deterministic_overlap_12s_3s_v1"
CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY = "deterministic_overlap_12s_3s_repeat_consensus_v1"


def transcribe_audio_chunked_12s_3s(
    audio_wav: str | Path,
    *,
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
) -> TranscriptResult:
    """Run the internal 12s/3s repeat-consensus evidence profile.

    Phase 2E keeps the generic deterministic ownership merge untouched. This
    profile adds only the narrowly gated exact-repeat consensus reconciliation
    and records that fact explicitly in transcript strategy metadata.
    """
    return transcribe_audio_chunked_with_repeat_consensus(
        audio_wav,
        model_name=model_name,
        language=language,
        device=device,
        compute_type=compute_type,
        window_seconds=CHUNKED_TRANSCRIPTION_WINDOW_SECONDS,
        hop_seconds=CHUNKED_TRANSCRIPTION_12S_3S_HOP_SECONDS,
        strategy=CHUNKED_TRANSCRIPTION_12S_3S_STRATEGY,
    )
