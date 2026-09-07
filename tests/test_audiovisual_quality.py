import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.approval import sha256_path
from video_tunner.audiovisual_quality import (
    build_audiovisual_quality_audit,
    parse_loudnorm_measurement,
)


def _measurement(*, integrated=-18.0, peak=-2.0):
    return {
        "integrated_lufs": integrated,
        "true_peak_dbtp": peak,
        "loudness_range_lu": 1.2,
        "threshold_lufs": -28.0,
    }


class AudiovisualQualityAuditTests(unittest.TestCase):
    def _fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        source = root / "source.mp4"
        output = root / "output.mp4"
        source.write_bytes(b"phase3-source")
        output.write_bytes(b"phase3-output")
        report = {
            "schema_version": 1,
            "record_type": "semantic_render_verification",
            "status": "technical_post_render_pass",
            "technical_pass": True,
            "blockers": [],
            "source": {"sha256": sha256_path(source)},
            "output": {"sha256": sha256_path(output)},
            "post_render_join_audits": [
                {
                    "id": "post-render-join-0001",
                    "status": "acoustic_context_only",
                    "technical_pass": True,
                }
            ],
            "auto_apply": False,
        }
        return temp, source, output, report

    def test_loudnorm_json_parser_uses_input_measurements_only(self):
        stderr = """
        irrelevant ffmpeg text
        {
            "input_i" : "-18.42",
            "input_tp" : "-2.17",
            "input_lra" : "1.30",
            "input_thresh" : "-28.65",
            "output_i" : "-15.95",
            "output_tp" : "-1.50",
            "output_lra" : "1.20",
            "output_thresh" : "-26.00",
            "normalization_type" : "dynamic",
            "target_offset" : "-0.05"
        }
        trailing text
        """
        parsed = parse_loudnorm_measurement(stderr)
        self.assertEqual(parsed["integrated_lufs"], -18.42)
        self.assertEqual(parsed["true_peak_dbtp"], -2.17)
        self.assertEqual(parsed["loudness_range_lu"], 1.3)
        self.assertEqual(parsed["threshold_lufs"], -28.65)

    def test_valid_audit_is_measurement_only_and_bound_to_phase2e(self):
        temp, source, output, technical = self._fixture()
        self.addCleanup(temp.cleanup)
        with patch(
            "video_tunner.audiovisual_quality.measure_audio_loudness",
            side_effect=[_measurement(integrated=-20.0, peak=-3.0), _measurement(integrated=-19.5, peak=-2.5)],
        ):
            audit = build_audiovisual_quality_audit(
                source,
                output,
                technical,
                technical_report_sha256="a" * 64,
            )
        self.assertEqual(audit["status"], "quality_audit_complete")
        self.assertTrue(audit["valid"])
        self.assertEqual(audit["phase2e_binding"]["source_sha256"], sha256_path(source))
        self.assertEqual(audit["phase2e_binding"]["output_sha256"], sha256_path(output))
        self.assertEqual(audit["measurements"]["delta"]["integrated_loudness_delta_lu"], 0.5)
        self.assertFalse(audit["treatment_authorized"])
        self.assertFalse(audit["treatment_policy"]["normalization_authorized"])
        self.assertFalse(audit["treatment_policy"]["denoise_authorized"])
        self.assertFalse(audit["treatment_policy"]["join_smoothing_authorized"])
        self.assertFalse(audit["auto_apply"])

    def test_true_peak_over_zero_is_risk_not_treatment_authorization(self):
        temp, source, output, technical = self._fixture()
        self.addCleanup(temp.cleanup)
        with patch(
            "video_tunner.audiovisual_quality.measure_audio_loudness",
            side_effect=[_measurement(peak=-1.0), _measurement(peak=0.4)],
        ):
            audit = build_audiovisual_quality_audit(
                source,
                output,
                technical,
                technical_report_sha256="b" * 64,
            )
        self.assertEqual(audit["summary"]["risk_count"], 1)
        self.assertEqual(audit["findings"][0]["code"], "output_true_peak_above_0_dbtp")
        self.assertTrue(audit["summary"]["quality_review_required"])
        self.assertFalse(audit["treatment_authorized"])

    def test_phase3_cannot_rescue_failed_phase2e_report(self):
        temp, source, output, technical = self._fixture()
        self.addCleanup(temp.cleanup)
        technical["technical_pass"] = False
        technical["status"] = "technical_post_render_failed"
        technical["blockers"] = [{"code": "post_render_join_gate_failed"}]
        with self.assertRaisesRegex(ValueError, "no puede rescatar"):
            build_audiovisual_quality_audit(
                source,
                output,
                technical,
                technical_report_sha256="c" * 64,
            )

    def test_phase3_cannot_rescue_failed_join_inside_passing_claim(self):
        temp, source, output, technical = self._fixture()
        self.addCleanup(temp.cleanup)
        technical["post_render_join_audits"][0]["technical_pass"] = False
        with self.assertRaisesRegex(ValueError, "no puede rescatar joins"):
            build_audiovisual_quality_audit(
                source,
                output,
                technical,
                technical_report_sha256="d" * 64,
            )

    def test_changed_output_sha_is_stale_evidence(self):
        temp, source, output, technical = self._fixture()
        self.addCleanup(temp.cleanup)
        output.write_bytes(b"tampered-after-phase2e")
        with self.assertRaisesRegex(ValueError, "Output SHA-256 no coincide"):
            build_audiovisual_quality_audit(
                source,
                output,
                technical,
                technical_report_sha256="e" * 64,
            )

    def test_nonfinite_loudnorm_values_are_preserved_as_unavailable(self):
        stderr = json.dumps(
            {
                "input_i": "-inf",
                "input_tp": "-inf",
                "input_lra": "0.00",
                "input_thresh": "-70.00",
                "output_i": "-inf",
                "output_tp": "-inf",
                "output_lra": "0.00",
                "output_thresh": "-70.00",
                "normalization_type": "linear",
                "target_offset": "0.00",
            },
            indent=4,
        )
        parsed = parse_loudnorm_measurement(stderr)
        self.assertIsNone(parsed["integrated_lufs"])
        self.assertIsNone(parsed["true_peak_dbtp"])


if __name__ == "__main__":
    unittest.main()
