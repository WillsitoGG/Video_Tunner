import math
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from video_tunner.approval import sha256_path
from video_tunner.noise_audit import (
    MIN_NON_SPEECH_TOTAL_SECONDS,
    MIN_NON_SPEECH_WINDOWS,
    NON_SPEECH_GUARD_SECONDS,
    NOISE_FRAME_SECONDS,
    build_noise_evidence_audit,
)


class NoiseEvidenceAuditTests(unittest.TestCase):
    @staticmethod
    def _quality(output: Path) -> dict:
        return {
            "schema_version": 1,
            "record_type": "audiovisual_quality_audit",
            "status": "quality_audit_complete",
            "valid": True,
            "phase2e_binding": {
                "required_status": "technical_post_render_pass",
                "technical_report_sha256": "a" * 64,
                "source_sha256": "b" * 64,
                "output_sha256": sha256_path(output),
                "join_count": 1,
            },
            "measurements": {},
            "findings": [],
            "summary": {"finding_count": 0, "risk_count": 0},
            "treatment_authorized": False,
            "auto_apply": False,
        }

    @staticmethod
    def _write_wav(path: Path, *, duration: float = 8.0, digital_silence: bool = False) -> None:
        sample_rate = 16000
        total = int(duration * sample_rate)
        frames = bytearray()
        for index in range(total):
            t = index / sample_rate
            speech = (1.0 <= t < 2.0) or (4.0 <= t < 5.0)
            if speech:
                value = int(2500 * math.sin(2.0 * math.pi * 440.0 * t))
            else:
                value = 0 if digital_silence else int(120 * math.sin(2.0 * math.pi * 97.0 * t))
            frames += int(value).to_bytes(2, byteorder="little", signed=True)
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(frames))

    def _run(self, root: Path, speech, *, digital_silence: bool = False):
        output = root / "phase2e-output.mp4"
        output.write_bytes(b"immutable-phase2e-output")
        quality = self._quality(output)

        def fake_extract(_source, destination, *, sample_rate=16000):
            self.assertEqual(sample_rate, 16000)
            self._write_wav(Path(destination), digital_silence=digital_silence)
            return Path(destination)

        with patch("video_tunner.noise_audit.extract_analysis_audio", side_effect=fake_extract):
            report = build_noise_evidence_audit(
                output,
                quality,
                speech,
                quality_audit_sha256="c" * 64,
                speech_evidence_sha256="d" * 64,
            )
        return output, quality, report

    def test_sufficient_measurement_is_non_executable_and_never_authorizes_denoise(self):
        with tempfile.TemporaryDirectory() as temp:
            output, _quality, report = self._run(
                Path(temp),
                [(1.0, 2.0), (4.0, 5.0)],
            )
            self.assertEqual(report["status"], "noise_measurement_complete")
            self.assertTrue(report["evidence_sufficient"])
            self.assertGreaterEqual(report["coverage"]["non_speech_window_count"], MIN_NON_SPEECH_WINDOWS)
            self.assertGreaterEqual(report["coverage"]["non_speech_seconds"], MIN_NON_SPEECH_TOTAL_SECONDS)
            self.assertGreater(report["measurements"]["speech_to_non_speech_median_rms_delta_db"], 10.0)
            self.assertFalse(report["treatment_policy"]["denoise_evaluated"])
            self.assertFalse(report["treatment_policy"]["denoise_authorized"])
            self.assertFalse(report["treatment_policy"]["filter_selected"])
            self.assertFalse(report["executable"])
            self.assertFalse(report["treatment_authorized"])
            self.assertFalse(report["auto_apply"])
            self.assertEqual(sha256_path(output), report["quality_binding"]["output_sha256"])

    def test_non_speech_windows_are_guarded_away_from_speech_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            _output, _quality, report = self._run(
                Path(temp),
                [(1.0, 2.0), (4.0, 5.0)],
            )
            windows = report["window_evidence"]["derived_non_speech_windows"]
            self.assertEqual(windows[0], {"start": 0.0, "end": 1.0 - NON_SPEECH_GUARD_SECONDS})
            self.assertEqual(windows[1], {"start": 2.0 + NON_SPEECH_GUARD_SECONDS, "end": 4.0 - NON_SPEECH_GUARD_SECONDS})
            self.assertEqual(windows[2], {"start": 5.0 + NON_SPEECH_GUARD_SECONDS, "end": 8.0})
            self.assertEqual(report["measurements"]["non_speech_energy"]["frame_seconds"], NOISE_FRAME_SECONDS)

    def test_insufficient_coverage_is_not_reclassified_as_noise_problem(self):
        with tempfile.TemporaryDirectory() as temp:
            _output, _quality, report = self._run(Path(temp), [(0.0, 7.0)])
            self.assertEqual(report["status"], "insufficient_noise_evidence")
            self.assertFalse(report["evidence_sufficient"])
            self.assertFalse(report["treatment_policy"]["denoise_authorized"])
            self.assertIn("not evidence that denoise is needed", report["interpretation"]["insufficient_note"])

    def test_digital_silence_is_recorded_without_inventing_dbfs_floor(self):
        with tempfile.TemporaryDirectory() as temp:
            _output, _quality, report = self._run(
                Path(temp),
                [(1.0, 2.0), (4.0, 5.0)],
                digital_silence=True,
            )
            energy = report["measurements"]["non_speech_energy"]
            self.assertGreater(energy["digital_silence_frame_count"], 0)
            self.assertIsNone(energy["median_rms_dbfs"])
            self.assertIsNone(report["measurements"]["speech_to_non_speech_median_rms_delta_db"])
            self.assertTrue(report["evidence_sufficient"])

    def test_changed_output_sha_fails_closed_before_measurement(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "phase2e-output.mp4"
            output.write_bytes(b"before")
            quality = self._quality(output)
            output.write_bytes(b"after")
            with self.assertRaisesRegex(ValueError, "evidence stale"):
                build_noise_evidence_audit(
                    output,
                    quality,
                    [(1.0, 2.0)],
                    quality_audit_sha256="c" * 64,
                    speech_evidence_sha256="d" * 64,
                )

    def test_overlapping_speech_intervals_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "phase2e-output.mp4"
            output.write_bytes(b"immutable")
            quality = self._quality(output)

            def fake_extract(_source, destination, *, sample_rate=16000):
                self._write_wav(Path(destination))
                return Path(destination)

            with patch("video_tunner.noise_audit.extract_analysis_audio", side_effect=fake_extract):
                with self.assertRaisesRegex(ValueError, "solapados"):
                    build_noise_evidence_audit(
                        output,
                        quality,
                        [(1.0, 2.0), (1.9, 3.0)],
                        quality_audit_sha256="c" * 64,
                        speech_evidence_sha256="d" * 64,
                    )

    def test_out_of_timeline_speech_interval_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "phase2e-output.mp4"
            output.write_bytes(b"immutable")
            quality = self._quality(output)

            def fake_extract(_source, destination, *, sample_rate=16000):
                self._write_wav(Path(destination))
                return Path(destination)

            with patch("video_tunner.noise_audit.extract_analysis_audio", side_effect=fake_extract):
                with self.assertRaisesRegex(ValueError, "fuera de la timeline"):
                    build_noise_evidence_audit(
                        output,
                        quality,
                        [(7.5, 8.5)],
                        quality_audit_sha256="c" * 64,
                        speech_evidence_sha256="d" * 64,
                    )

    def test_invalid_speech_evidence_sha_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "phase2e-output.mp4"
            output.write_bytes(b"immutable")
            quality = self._quality(output)
            with self.assertRaisesRegex(ValueError, "speech_evidence_sha256"):
                build_noise_evidence_audit(
                    output,
                    quality,
                    [],
                    quality_audit_sha256="c" * 64,
                    speech_evidence_sha256="not-a-sha",
                )


if __name__ == "__main__":
    unittest.main()
