from __future__ import annotations

import importlib.util
import unittest


NUMPY_AVAILABLE = importlib.util.find_spec("numpy") is not None


@unittest.skipUnless(NUMPY_AVAILABLE, "NumPy no instalado; sync automático pertenece al perfil analysis")
class SyncEstimatorTests(unittest.TestCase):
    @staticmethod
    def _synthetic_pair(offset: float, scale: float, *, duration: float = 150.0, rate: int = 50):
        import numpy as np

        rng = np.random.default_rng(20260902)
        count = int(duration * rate)
        camera = np.zeros(count, dtype=float)
        for _ in range(320):
            start = int(rng.integers(0, max(1, count - 100)))
            length = int(rng.integers(10, 120))
            amplitude = float(rng.uniform(0.1, 2.0))
            usable = min(length, count - start)
            if usable > 1:
                camera[start : start + usable] += amplitude * np.hanning(usable)
        camera += 0.02 * rng.normal(size=count)
        camera = np.maximum(camera, 0.0)

        external_duration = (duration - offset) / scale
        external_time = np.arange(int(external_duration * rate), dtype=float) / rate
        mapped_video_time = offset + scale * external_time
        external = np.interp(
            mapped_video_time,
            np.arange(count, dtype=float) / rate,
            camera,
            left=0.0,
            right=0.0,
        )
        external += 0.01 * rng.normal(size=len(external))
        return camera, np.maximum(external, 0.0)

    def test_recovers_positive_offset(self):
        from video_tunner.sync import estimate_sync_from_envelopes

        camera, external = self._synthetic_pair(2.0, 1.0)
        estimate = estimate_sync_from_envelopes(camera, external)
        self.assertAlmostEqual(estimate.offset_seconds, 2.0, delta=0.03)
        self.assertAlmostEqual(estimate.drift_ppm, 0.0, delta=100.0)
        self.assertGreater(estimate.confidence, 0.80)
        self.assertGreaterEqual(len(estimate.anchors), 5)

    def test_recovers_negative_offset(self):
        from video_tunner.sync import estimate_sync_from_envelopes

        camera, external = self._synthetic_pair(-1.5, 1.0)
        estimate = estimate_sync_from_envelopes(camera, external)
        self.assertAlmostEqual(estimate.offset_seconds, -1.5, delta=0.03)
        self.assertGreater(estimate.confidence, 0.80)

    def test_recovers_linear_clock_drift(self):
        from video_tunner.sync import estimate_sync_from_envelopes

        camera, external = self._synthetic_pair(1.25, 1.0009)
        estimate = estimate_sync_from_envelopes(camera, external)
        self.assertAlmostEqual(estimate.offset_seconds, 1.25, delta=0.04)
        self.assertAlmostEqual(estimate.drift_ppm, 900.0, delta=120.0)
        self.assertLess(estimate.residual_rms_seconds, 0.03)
        self.assertGreater(estimate.confidence, 0.80)

    def test_rejects_flat_signal(self):
        import numpy as np

        from video_tunner.sync import SyncInsufficientSignalError, estimate_sync_from_envelopes

        flat = np.zeros(5000, dtype=float)
        with self.assertRaises(SyncInsufficientSignalError):
            estimate_sync_from_envelopes(flat, flat)


if __name__ == "__main__":
    unittest.main()
