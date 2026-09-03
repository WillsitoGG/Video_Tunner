import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.analysis_pipeline import analyze_spoken_video
from video_tunner.transcription import TranscriptResult, TranscriptSegment, WordTiming
from video_tunner.vad import SpeechInterval


def timed_transcript(text: str) -> TranscriptResult:
    tokens = text.split()
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


def fake_acoustic_assessments(_master, joins):
    results = []
    for index, join in enumerate(joins, start=1):
        clean = join.get("status") == "join_context_only"
        results.append(
            {
                "id": f"acoustic-join-assessment-{index:04d}",
                "join_assessment_id": join.get("id"),
                "candidate_id": join.get("candidate_id"),
                "candidate_kind": join.get("candidate_kind"),
                "status": "acoustic_context_only" if clean else "blocked_by_context",
                "target_span": join.get("target_span"),
                "metrics": (
                    {
                        "measurement_available": True,
                        "sample_rate": 16000,
                        "rms_delta_db": 0.0,
                        "boundary_sample_jump": 0.0,
                        "boundary_jump_ratio": 0.0,
                    }
                    if clean
                    else None
                ),
                "rationale": ["fixture de integración; decode real cubierto aparte"],
                "measurement_available": clean,
                "safe_for_cut": False,
                "executable": False,
                "auto_apply": False,
            }
        )
    return results


def run_fake_analysis(transcript: TranscriptResult) -> dict:
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
                return_value=transcript,
            ),
            patch(
                "video_tunner.analysis_pipeline.detect_speech",
                return_value=[SpeechInterval(0.0, 3.0)],
            ),
            patch(
                "video_tunner.analysis_pipeline.build_acoustic_join_assessments",
                side_effect=fake_acoustic_assessments,
            ),
        ):
            result = analyze_spoken_video(
                source,
                root / "Output",
                mode="conservative",
                language="es",
            )

        return json.loads(Path(result["analysis"]).read_text(encoding="utf-8"))


class SemanticPipelineIntegrationTests(unittest.TestCase):
    def test_analyze_emits_candidate_decision_join_and_acoustic_evidence_for_repetition(self):
        report = run_fake_analysis(
            timed_transcript("vamos a lanzar vamos a lanzar el producto mañana")
        )
        repetition = next(
            item for item in report["candidates"] if item["kind"] == "possible_repetition"
        )
        self.assertEqual(repetition["id"], "possible_repetition-0001")
        self.assertEqual(repetition["evidence"]["removed_text"], "vamos a lanzar")
        self.assertEqual(repetition["evidence"]["keep_occurrence"], "later")
        self.assertEqual(repetition["suggested_decision"], "REVIEW")
        self.assertFalse(repetition["auto_apply"])

        decision = next(
            item
            for item in report["semantic_decisions"]
            if item["candidate_id"] == repetition["id"]
        )
        join = next(
            item for item in report["join_assessments"] if item["candidate_id"] == repetition["id"]
        )
        acoustic = next(
            item
            for item in report["acoustic_join_assessments"]
            if item["join_assessment_id"] == join["id"]
        )
        self.assertEqual(report["schema_version"], 7)
        self.assertEqual(report["correction_scopes"], [])
        self.assertEqual(report["summary"]["correction_scopes"]["count"], 0)
        self.assertEqual(report["filler_assessments"], [])
        self.assertEqual(report["summary"]["filler_assessments"]["count"], 0)
        self.assertEqual(join["status"], "transcript_edge")
        self.assertEqual(acoustic["status"], "blocked_by_context")
        self.assertFalse(acoustic["measurement_available"])
        self.assertFalse(acoustic["safe_for_cut"])
        self.assertFalse(acoustic["executable"])
        self.assertFalse(acoustic["auto_apply"])
        self.assertEqual(decision["decision"], "PROPOSED_CUT")
        self.assertEqual(decision["guard_status"], "pass")
        self.assertFalse(decision["executable"])
        self.assertFalse(decision["auto_apply"])
        self.assertEqual(report["summary"]["automatic_edits"], 0)
        self.assertEqual(report["summary"]["semantic_decisions"]["executable"], 0)
        self.assertEqual(report["summary"]["join_assessments"]["safe_for_cut"], 0)
        self.assertEqual(report["summary"]["acoustic_join_assessments"]["safe_for_cut"], 0)
        self.assertTrue(report["safety"]["join_acoustic_validation_enabled"])
        self.assertTrue(report["safety"]["join_acoustic_validation_is_not_cut_authorization"])

    def test_analyze_links_correction_scope_join_acoustic_evidence_and_review_decision(self):
        report = run_fake_analysis(
            timed_transcript("la facturación fue de 200 perdón de 250 mil euros")
        )
        correction = next(
            item for item in report["candidates"] if item["kind"] == "explicit_correction"
        )
        scope = next(
            item for item in report["correction_scopes"] if item["candidate_id"] == correction["id"]
        )
        join = next(
            item for item in report["join_assessments"] if item["candidate_id"] == correction["id"]
        )
        acoustic = next(
            item
            for item in report["acoustic_join_assessments"]
            if item["join_assessment_id"] == join["id"]
        )
        decision = next(
            item for item in report["semantic_decisions"] if item["candidate_id"] == correction["id"]
        )

        self.assertEqual(report["schema_version"], 7)
        self.assertEqual(scope["status"], "bounded")
        self.assertEqual(scope["strategy"], "repeated_corrected_prefix_anchor")
        self.assertEqual(scope["attempt_span"]["text"], "de 200")
        self.assertEqual(scope["marker_span"]["text"], "perdón")
        self.assertFalse(scope["safe_for_cut"])
        self.assertFalse(scope["executable"])
        self.assertFalse(scope["auto_apply"])
        self.assertEqual(report["filler_assessments"], [])
        self.assertEqual(join["status"], "repair_or_protected_context_risk")
        self.assertEqual(join["target_span"]["source"], "bounded_correction_attempt_plus_marker")
        self.assertEqual(join["target_span"]["text"], "de 200 perdón")
        self.assertEqual(acoustic["status"], "blocked_by_context")
        self.assertFalse(acoustic["measurement_available"])
        self.assertFalse(join["safe_for_cut"])
        self.assertFalse(acoustic["safe_for_cut"])
        self.assertEqual(decision["decision"], "REVIEW")
        self.assertFalse(decision["executable"])
        self.assertEqual(report["summary"]["automatic_edits"], 0)
        self.assertEqual(report["summary"]["correction_scopes"]["safe_for_cut"], 0)
        self.assertEqual(report["summary"]["correction_scopes"]["executable"], 0)
        self.assertEqual(report["summary"]["correction_scopes"]["auto_apply"], 0)
        self.assertEqual(report["summary"]["join_assessments"]["safe_for_cut"], 0)
        self.assertEqual(report["summary"]["acoustic_join_assessments"]["safe_for_cut"], 0)


if __name__ == "__main__":
    unittest.main()
