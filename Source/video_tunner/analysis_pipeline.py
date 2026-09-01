from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .audio import extract_analysis_audio
from .candidates import build_analysis_report, build_candidates, save_analysis_report
from .edit_plan import MODE_SETTINGS
from .media import probe_media
from .transcription import (
    transcribe_audio,
    write_srt,
    write_transcript_json,
    write_transcript_txt,
)
from .vad import detect_speech


def analyze_spoken_video(
    source: str | Path,
    output_dir: str | Path,
    *,
    mode: str = "conservative",
    model_name: str = "large-v3-turbo",
    language: str | None = None,
    device: str = "auto",
    compute_type: str = "auto",
) -> dict[str, Any]:
    """Run local transcription + VAD and emit review-only candidate artifacts."""
    if mode not in MODE_SETTINGS:
        raise ValueError(f"Modo desconocido: {mode}")
    source_path = Path(source)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    probe = probe_media(source_path)
    if probe["audio_streams"] < 1:
        raise ValueError("El vídeo no contiene una pista de audio analizable.")

    with tempfile.TemporaryDirectory(prefix=".video_tunner_analysis_", dir=output_root) as temp:
        wav_path = extract_analysis_audio(source_path, Path(temp) / "analysis.wav")
        transcript = transcribe_audio(
            wav_path,
            model_name=model_name,
            language=language,
            device=device,
            compute_type=compute_type,
        )
        speech = detect_speech(
            wav_path,
            min_silence_ms=250,
            speech_pad_ms=100,
        )

    candidates = build_candidates(
        transcript,
        speech,
        duration=float(probe["duration_seconds"]),
        mode=mode,
    )

    stem = source_path.stem
    transcript_json = write_transcript_json(transcript, output_root / f"{stem}_transcript.json")
    transcript_txt = write_transcript_txt(transcript, output_root / f"{stem}_transcript.txt")
    subtitles = write_srt(transcript, output_root / f"{stem}.srt")
    report = build_analysis_report(
        source_path,
        probe,
        transcript,
        speech,
        mode=mode,
        candidates=candidates,
    )
    analysis_path = save_analysis_report(report, output_root / f"{stem}_analysis.json")

    return {
        "analysis": str(analysis_path),
        "transcript_json": str(transcript_json),
        "transcript_txt": str(transcript_txt),
        "subtitles_srt": str(subtitles),
        "summary": report["summary"],
    }
