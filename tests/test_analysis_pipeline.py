import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.analysis_pipeline import analyze_spoken_video
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming
from video_tunner.vad import SpeechInterval


def _sample_transcript() -> TranscriptResult:
    return TranscriptResult(
        language="es",
        language_probability=0.99,
        model="large-v3-turbo",
        device="cpu",
        compute_type="int8",
        segments=(
            TranscriptSegment(
                text="Hola eh seguimos",
                start=0.1,
                end=2.5,
                words=(
                    WordTiming("Hola", 0.1, 0.5, 0.99),
                    WordTiming("eh", 0.6, 0.9, 0.90),
                    WordTiming("seguimos", 1.8, 2.5, 0.98),
                ),
            ),
        ),
    )


class AnalysisPipelineTests(unittest.TestCase):
    @staticmethod
    def _write_ingest_report(source: Path, master: Path, destination: Path, *, status: str = "ready") -> None:
        payload = {
            "schema_version": 1,
            "status": status,
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
        destination.write_text(json.dumps(payload), encoding="utf-8")

    def test_pipeline_uses_the_same_verified_master_for_whisper_and_vad(self):
        transcript = _sample_transcript()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "video source.mp4"
            source.write_bytes(b"fake-video")
            master = root / "video source_master_audio.flac"
            master.write_bytes(b"fake-master")
            ingest_report = root / "video source_ingest.json"
            self._write_ingest_report(source, master, ingest_report)
            output = root / "out"

            def fake_probe(path):
                path = Path(path)
                if path == source:
                    return {"duration_seconds": 3.0, "audio_streams": 1, "video_streams": 1}
                if path == master:
                    return {"duration_seconds": 3.0, "audio_streams": 1, "video_streams": 0}
                raise AssertionError(f"probe inesperado: {path}")

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
                patch("video_tunner.analysis_pipeline.transcribe_audio", return_value=transcript) as transcribe,
                patch(
                    "video_tunner.analysis_pipeline.detect_speech",
                    return_value=[SpeechInterval(0.05, 1.0), SpeechInterval(1.75, 2.7)],
                ) as vad,
            ):
                result = analyze_spoken_video(source, output, mode="conservative", language="es")

            self.assertEqual(result["status"], "analyzed")
            self.assertEqual(Path(result["master_audio"]), master)
            transcribe.assert_called_once()
            vad.assert_called_once()
            self.assertEqual(Path(transcribe.call_args.args[0]), master)
            self.assertEqual(Path(vad.call_args.args[0]), master)

            for key in ("analysis", "transcript_json", "transcript_txt", "subtitles_srt"):
                self.assertTrue(Path(result[key]).is_file(), key)
            report = json.loads(Path(result["analysis"]).read_text(encoding="utf-8"))
            self.assertEqual(report["schema_version"], 4)
            self.assertEqual(report["input"]["master_audio"]["file"], master.name)
            self.assertEqual(report["input"]["ingest"]["status"], "ready")
            self.assertTrue(report["safety"]["master_audio_is_timeline_source"])
            self.assertTrue(report["safety"]["semantic_protection_enabled"])
            self.assertTrue(report["safety"]["semantic_decisions_are_not_edits"])
            self.assertFalse(report["safety"]["semantic_decisions_executable"])
            self.assertTrue(report["safety"]["correction_scopes_are_not_edits"])
            self.assertFalse(report["safety"]["correction_scopes_executable"])
            self.assertFalse(report["safety"]["correction_scopes_safe_for_cut"])
            self.assertEqual(report["semantic_decisions"], [])
            self.assertEqual(report["correction_scopes"], [])
            self.assertEqual(report["summary"]["correction_scopes"]["count"], 0)
            self.assertEqual(report["summary"]["automatic_edits"], 0)

    def test_review_required_stops_before_whisper_or_vad(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "video.mp4"
            source.write_bytes(b"fake-video")
            ingest_report = root / "video_ingest.json"
            ingest_report.write_text("{}", encoding="utf-8")

            with (
                patch(
                    "video_tunner.analysis_pipeline.probe_media",
                    return_value={"duration_seconds": 10.0, "audio_streams": 1, "video_streams": 1},
                ),
                patch(
                    "video_tunner.analysis_pipeline.ingest_video",
                    return_value={
                        "status": "review_required",
                        "master_audio": None,
                        "ingest_report": str(ingest_report),
                        "review_reasons": ["evidencia insuficiente"],
                    },
                ),
                patch("video_tunner.analysis_pipeline.transcribe_audio") as transcribe,
                patch("video_tunner.analysis_pipeline.detect_speech") as vad,
            ):
                result = analyze_spoken_video(source, root / "out")

            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["stage"], "ingest")
            self.assertIsNone(result["master_audio"])
            transcribe.assert_not_called()
            vad.assert_not_called()

    def test_pre_resolved_master_requires_matching_ingest_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "video.mp4"
            source.write_bytes(b"actual-video")
            master = root / "master.flac"
            master.write_bytes(b"master")
            ingest_report = root / "wrong_ingest.json"
            payload = {
                "status": "ready_auto",
                "video": {"sha256": "0" * 64},
                "master_audio": {"file": master.name},
                "sync": {"method": "auto_correlation"},
            }
            ingest_report.write_text(json.dumps(payload), encoding="utf-8")

            def fake_probe(path):
                return (
                    {"duration_seconds": 5.0, "audio_streams": 1, "video_streams": 1}
                    if Path(path) == source
                    else {"duration_seconds": 5.0, "audio_streams": 1, "video_streams": 0}
                )

            with patch("video_tunner.analysis_pipeline.probe_media", side_effect=fake_probe):
                with self.assertRaisesRegex(ValueError, "vídeo fuente diferente"):
                    analyze_spoken_video(
                        source,
                        root / "out",
                        master_audio=master,
                        ingest_report_path=ingest_report,
                    )

    def test_pre_resolved_master_requires_ingest_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "video.mp4"
            source.write_bytes(b"video")
            master = root / "master.flac"
            master.write_bytes(b"master")
            with patch(
                "video_tunner.analysis_pipeline.probe_media",
                return_value={"duration_seconds": 5.0, "audio_streams": 1, "video_streams": 1},
            ):
                with self.assertRaisesRegex(ValueError, "requiere también --ingest-report"):
                    analyze_spoken_video(source, root / "out", master_audio=master)


if __name__ == "__main__":
    unittest.main()
