import hashlib
import json
import math
import unittest
from pathlib import Path

import numpy as np

from video_tunner.denoise_objective import (
    DENOISE_OBJECTIVE_POLICY_ID,
    build_denoise_objective_measurement,
    compute_paired_objective_metrics,
    scale_invariant_sdr,
)


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoise_objective_metric_policy_v1.json"
CORPUS = ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
EXPECTED_CORPUS_SHA256 = "49e742ce7912d008ee5ef3cc3bd5a31b4c9f117125aa2a811b2a6bd00acb1c03"


class DenoiseObjectiveMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_metric_policy_is_frozen_before_algorithm_comparison_and_non_executable(self):
        policy = self.policy
        self.assertEqual(policy["policy_id"], DENOISE_OBJECTIVE_POLICY_ID)
        self.assertEqual(hashlib.sha256(CORPUS.read_bytes()).hexdigest(), EXPECTED_CORPUS_SHA256)
        self.assertEqual(policy["corpus_fixture_sha256"], EXPECTED_CORPUS_SHA256)
        baseline = policy["baseline_policy"]
        self.assertFalse(baseline["acceptance_thresholds_defined"])
        self.assertFalse(baseline["algorithm_ranking_allowed"])
        self.assertFalse(baseline["denoiser_selected"])
        self.assertFalse(baseline["denoise_authorized"])
        self.assertFalse(baseline["renderer_authorized"])
        self.assertFalse(baseline["auto_apply"])

    def test_metric_policy_uses_sisdr_and_classic_stoi_only(self):
        metrics = self.policy["metrics"]
        self.assertEqual(set(metrics), {"si_sdr", "stoi"})
        self.assertTrue(metrics["si_sdr"]["enabled"])
        self.assertTrue(metrics["stoi"]["enabled"])
        self.assertFalse(metrics["stoi"]["extended"])
        self.assertEqual(metrics["stoi"]["pystoi_version"], "0.4.1")
        self.assertEqual(metrics["stoi"]["scipy_version"], "1.18.1")
        self.assertIn("pesq", self.policy["excluded_metrics"])

    def test_sisdr_is_scale_invariant(self):
        t = np.linspace(0.0, 1.0, 4800, endpoint=False)
        clean = np.sin(2.0 * np.pi * 220.0 * t)
        noise = 0.05 * np.sin(2.0 * np.pi * 997.0 * t)
        a = scale_invariant_sdr(clean, clean + noise)
        b = scale_invariant_sdr(clean, 3.0 * (clean + noise))
        self.assertAlmostEqual(a, b, places=9)

    def test_sisdr_rejects_length_mismatch_and_silent_reference(self):
        with self.assertRaises(ValueError):
            scale_invariant_sdr(np.ones(10), np.ones(11))
        with self.assertRaises(ValueError):
            scale_invariant_sdr(np.zeros(10), np.ones(10))

    def test_paired_metrics_require_finite_stoi_inside_closed_interval(self):
        clean = np.linspace(-0.5, 0.5, 1000)
        noisy = clean + 0.02 * np.sin(np.linspace(0, 10, 1000))
        for invalid in (-0.01, 1.01, float("nan")):
            with self.assertRaises(ValueError):
                compute_paired_objective_metrics(
                    clean,
                    noisy,
                    sample_rate_hz=48000,
                    stoi_fn=lambda *_args, value=invalid, **_kwargs: value,
                )

    def test_measurement_is_auxiliary_only_and_has_no_treatment_capability(self):
        clean = np.linspace(-0.5, 0.5, 1000)
        noisy = clean + 0.02 * np.sin(np.linspace(0, 10, 1000))
        record = build_denoise_objective_measurement(
            case_id="case",
            clean_sha256="a" * 64,
            degraded_sha256="b" * 64,
            sample_rate_hz=48000,
            reference=clean,
            degraded=noisy,
            stoi_fn=lambda *_args, **_kwargs: 0.75,
        )
        self.assertEqual(record["record_type"], "denoise_objective_measurement")
        self.assertTrue(math.isfinite(record["metrics"]["si_sdr_db"]))
        self.assertEqual(record["metrics"]["stoi"], 0.75)
        interpretation = record["interpretation"]
        self.assertTrue(interpretation["objective_metrics_are_auxiliary_only"])
        self.assertFalse(interpretation["algorithm_ranking_authorized"])
        self.assertFalse(interpretation["denoiser_selected"])
        self.assertFalse(interpretation["denoise_authorized"])
        self.assertFalse(interpretation["renderer_authorized"])
        self.assertFalse(interpretation["auto_apply"])


if __name__ == "__main__":
    unittest.main()
