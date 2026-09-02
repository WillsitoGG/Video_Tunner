import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.analysis_pipeline import analyze_spoken_video
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming
from video_tunner.vad import SpeechInterval


def repeated_transcript() -> TranscriptResult:
    tokens = "vamos a lanzar vamos a lanzar el producto mañana".split()
    words = []
    cursor = 0.2
    for token in tokens:
        words.append(WordTiming(token, cursor, cursor + 0.22, 0.99))
        cursor += 0.30
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text=" ".join(tokens),
                start=words[0].start,
                end=words[-1].end,
                words=tuple(words),
            ),
        ),
    )


class SemanticPipelineIntegrationTests(unittest.TestCase):
    def test_analyze_emits_auditable_review_only_repetition(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "video.mp4"
            source.write_bytes(b"fake-video")
            master = root / "video_master_audio.flac"
            master.write_bytes(b"fake-master")
            ingest_report = root / "video_ingest.json"
            ingest_report.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "status": "ready",
                        "input_mode": "embedded_audio",
                        "video": {
                            "file": source.name,
                            "duration_seconds": 3.0,
                            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        },
                        "timeline_convention": "video_time = offset_seconds + time_scale * external_time",
                        "sync": {"method": "embedded", "required": False},
                        "master_audio": {"file": master.name, "source": "embedded_audio"},
                    }
                ),
                encoding="utf-8",
            )

            def fake_probe(path):
                if Path(path) == source:
                    return {"duration_seconds": 3.0, "audio_streams": 1, "video_streams": 1}
                if Path(path) == master:
                    return {"duration_seconds": 3.0, "audio_streams": 1, "video_streams": 0}
                raise AssertionError(path)

            with (
                patch("video_tunner.analysis_pipeline.probe_media", side_effect=fake_probe),
                patch(
                    "video_tunner.analysis_pipeline.ingest_video",
                    return_value={
                        "status": "ready",
                        "master_audio": str(master),
                        "ingest_report": str(ingest_report),
                    },
                ),
                patch(
                    "video_tunner.analysis_pipeline.transcribe_audio",
                    return_value=repeated_transcript(),
                ),
                patch(
                    "video_tunner.analysis_pipeline.detect_speech",
                    return_value=[SpeechInterval(0.0, 3.0)],
                ),
            ):
                result = analyze_spoken_video(
                    source,
                    root / "Output",
                    mode="conservative",
                    language="es",
                )

            report = json.loads(Path(result["analysis"]).read_text(encoding="utf-8"))
            repetition = next(
                item for item in report["candidates"] if item["kind"] == "possible_repetition"
            )
            self.assertEqual(repetition["id"], "possible_repetition-0001")
            self.assertEqual(repetition["evidence"]["removed_text"], "vamos a lanzar")
            self.assertEqual(repetition["evidence"]["keep_occurrence"], "later")
            self.assertEqual(repetition["suggested_decision"], "REVIEW")
            self.assertFalse(repetition["auto_apply"])
            self.assertEqual(report["summary"]["automatic_edits"], 0)


if __name__ == "__main__":
    unittest.main()
