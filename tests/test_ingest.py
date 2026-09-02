from __future__ import annotations

import unittest

from video_tunner.ingest import coverage_metrics, evaluate_auto_sync, external_alignment_filter
from video_tunner.sync import SyncAnchor, SyncEstimate


class IngestPolicyTests(unittest.TestCase):
    @staticmethod
    def _estimate(**overrides) -> SyncEstimate:
        values = {
            "offset_seconds": 1.0,
            "time_scale": 1.0,
            "drift_ppm": 0.0,
            "confidence": 0.90,
            "residual_rms_seconds": 0.02,
            "coarse_offset_seconds": 1.0,
            "coarse_score": 0.90,
            "anchors": tuple(
                SyncAnchor(
                    video_time=float(index * 20),
                    external_time=float(index * 20 - 1),
                    offset_seconds=1.0,
                    score=0.9,
                    uniqueness_margin=0.1,
                    residual_seconds=0.0,
                )
                for index in range(1, 6)
            ),
        }
        values.update(overrides)
        return SyncEstimate(**values)

    def test_coverage_respects_positive_offset(self):
        coverage = coverage_metrics(
            video_duration=100.0,
            external_duration=100.0,
            offset_seconds=2.0,
            time_scale=1.0,
        )
        self.assertAlmostEqual(coverage["coverage_ratio"], 0.98)
        self.assertAlmostEqual(coverage["uncovered_start_seconds"], 2.0)
        self.assertAlmostEqual(coverage["uncovered_end_seconds"], 0.0)

    def test_auto_sync_accepts_consistent_high_confidence_mapping(self):
        estimate = self._estimate()
        coverage = coverage_metrics(
            video_duration=100.0,
            external_duration=100.0,
            offset_seconds=1.0,
            time_scale=1.0,
        )
        accepted, reasons = evaluate_auto_sync(estimate, coverage)
        self.assertTrue(accepted)
        self.assertEqual(reasons, [])

    def test_auto_sync_rejects_low_confidence(self):
        estimate = self._estimate(confidence=0.30)
        coverage = coverage_metrics(
            video_duration=100.0,
            external_duration=100.0,
            offset_seconds=1.0,
            time_scale=1.0,
        )
        accepted, reasons = evaluate_auto_sync(estimate, coverage)
        self.assertFalse(accepted)
        self.assertTrue(any("confidence" in reason for reason in reasons))

    def test_positive_offset_filter_delays_external_audio(self):
        chain = external_alignment_filter(
            offset_seconds=1.25,
            time_scale=1.0,
            video_duration=60.0,
        )
        self.assertIn("adelay=1250:all=1", chain)
        self.assertIn("apad", chain)
        self.assertTrue(chain.endswith("atrim=0:60.000000000"))

    def test_negative_offset_filter_trims_preroll(self):
        chain = external_alignment_filter(
            offset_seconds=-2.5,
            time_scale=1.001,
            video_duration=60.0,
        )
        self.assertIn("atrim=start=2.500000000", chain)
        self.assertIn("asetpts=PTS-STARTPTS", chain)
        self.assertIn("atempo=0.999000999001", chain)


if __name__ == "__main__":
    unittest.main()
