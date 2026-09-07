import unittest

import numpy as np

from video_tunner.denoise_objective import (
    compute_clean_preservation_metrics,
    normalized_rmse,
    right_tail_normalize,
)


class DenoiseCandidateEvaluationPrimitiveTests(unittest.TestCase):
    def test_right_tail_pad_preserves_time_origin_and_only_appends_padding(self):
        source = np.array([0.1, -0.2, 0.3], dtype=np.float64)
        normalized, audit = right_tail_normalize(source, target_frame_count=5, padding_value=0.0)
        np.testing.assert_array_equal(normalized[:3], source)
        np.testing.assert_array_equal(normalized[3:], np.array([0.0, 0.0]))
        self.assertEqual(audit["action"], "right_pad")
        self.assertEqual(audit["raw_frame_delta"], -2)
        self.assertFalse(audit["alignment_search_performed"])
        self.assertFalse(audit["time_shift_performed"])
        self.assertFalse(audit["level_matching_performed"])

    def test_right_tail_trim_preserves_prefix_exactly(self):
        source = np.array([0.1, -0.2, 0.3, 0.4, 0.5], dtype=np.float64)
        normalized, audit = right_tail_normalize(source, target_frame_count=3)
        np.testing.assert_array_equal(normalized, source[:3])
        self.assertEqual(audit["action"], "right_trim")
        self.assertEqual(audit["raw_frame_delta"], 2)

    def test_right_tail_normalization_never_mutates_equal_length_input(self):
        source = np.array([0.1, -0.2, 0.3], dtype=np.float64)
        normalized, audit = right_tail_normalize(source, target_frame_count=3)
        np.testing.assert_array_equal(normalized, source)
        self.assertEqual(audit["action"], "none")
        self.assertIsNot(normalized, source)

    def test_normalized_rmse_is_zero_for_identity_and_scale_sensitive(self):
        clean = np.array([1.0, -1.0, 0.5, -0.5], dtype=np.float64)
        self.assertEqual(normalized_rmse(clean, clean), 0.0)
        self.assertGreater(normalized_rmse(clean, clean * 0.5), 0.0)

    def test_clean_preservation_returns_only_precommitted_metrics(self):
        clean = np.array([0.2, -0.2, 0.1, -0.1], dtype=np.float64)
        treated = clean * 0.9

        def fake_stoi(reference, estimate, sample_rate, extended=False):
            self.assertEqual(sample_rate, 48000)
            self.assertFalse(extended)
            return 0.98

        metrics = compute_clean_preservation_metrics(
            clean,
            treated,
            sample_rate_hz=48000,
            stoi_fn=fake_stoi,
        )
        self.assertEqual(set(metrics), {"stoi", "normalized_rmse"})
        self.assertEqual(metrics["stoi"], 0.98)
        self.assertGreater(metrics["normalized_rmse"], 0.0)

    def test_clean_preservation_rejects_shape_mismatch(self):
        with self.assertRaises(ValueError):
            compute_clean_preservation_metrics(
                np.array([0.1, 0.2, 0.3]),
                np.array([0.1, 0.2]),
                sample_rate_hz=48000,
                stoi_fn=lambda *args, **kwargs: 1.0,
            )


if __name__ == "__main__":
    unittest.main()
