import math
import shutil
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from video_tunner.acoustic_join import (
    SAMPLE_RATE,
    build_acoustic_join_assessments,
    classify_join_acoustics,
    measure_join_edges,
)


def _join(*, status="join_context_only", start=0.4, end=0.6):
    return {
        "id": "join-assessment-0001",
        "candidate_id": "possible_filler-0001",
        "candidate_kind": "possible_filler",
        "status": status,
        "target_span": {"start": start, "end": end, "text": "eh"},
        "safe_for_cut": False,
        "executable": False,
        "auto_apply": False,
    }


def _sine_window(amplitude=0.35, frequency=220.0, seconds=0.08, phase=0.0):
    count = int(round(SAMPLE_RATE * seconds))
    t = np.arange(count, dtype=np.float32) / SAMPLE_RATE
    return (amplitude * np.sin(2.0 * math.pi * frequency * t + phase)).astype(np.float32)


def _write_wav(path: Path, samples: np.ndarray) -> None:
    clipped = np.clip(samples, -0.999, 0.999)
    pcm = np.round(clipped * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(pcm.tobytes())


class AcousticJoinMetricTests(unittest.TestCase):
    def test_continuous_signal_is_context_only_not_safe(self):
        full = _sine_window(seconds=0.16)
        metrics = measure_join_edges(full[: len(full) // 2], full[len(full) // 2 :])
        status, _ = classify_join_acoustics(metrics)
        self.assertEqual(status, "acoustic_context_only")
        self.assertTrue(metrics["measurement_available"])

    def test_both_low_energy_edges_are_recorded_as_context(self):
        silence = np.zeros(int(SAMPLE_RATE * 0.08), dtype=np.float32)
        metrics = measure_join_edges(silence, silence)
        status, _ = classify_join_acoustics(metrics)
        self.assertEqual(status, "low_energy_boundary_context")

    def test_large_level_delta_is_risk(self):
        left = _sine_window(amplitude=0.05)
        right = _sine_window(amplitude=0.8)
        metrics = measure_join_edges(left, right)
        status, _ = classify_join_acoustics(metrics)
        self.assertIn(status, {"level_discontinuity_risk", "combined_discontinuity_risk"})
        self.assertGreater(metrics["rms_delta_db"], 12.0)

    def test_large_instantaneous_jump_is_waveform_risk(self):
        left = np.full(int(SAMPLE_RATE * 0.08), 0.4, dtype=np.float32)
        right = np.full(int(SAMPLE_RATE * 0.08), -0.4, dtype=np.float32)
        metrics = measure_join_edges(left, right)
        status, _ = classify_join_acoustics(metrics)
        self.assertEqual(status, "waveform_discontinuity_risk")
        self.assertGreater(metrics["boundary_sample_jump"], 0.35)
        self.assertGreater(metrics["boundary_jump_ratio"], 1.25)

    def test_empty_edge_fails_safe(self):
        metrics = measure_join_edges(np.array([], dtype=np.float32), np.ones(20, dtype=np.float32))
        status, _ = classify_join_acoustics(metrics)
        self.assertEqual(status, "insufficient_audio_context")

    def test_context_blocked_join_does_not_require_master_decode(self):
        result = build_acoustic_join_assessments(
            "this-file-does-not-exist.wav",
            [_join(status="critical_lexical_context_risk")],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["status"], "blocked_by_context")
        self.assertFalse(result[0]["measurement_available"])
        self.assertFalse(result[0]["safe_for_cut"])
        self.assertFalse(result[0]["executable"])
        self.assertFalse(result[0]["auto_apply"])


@unittest.skipUnless(shutil.which("ffmpeg"), "FFmpeg no disponible")
class AcousticJoinMasterAudioTests(unittest.TestCase):
    def test_real_pcm_decode_measures_continuous_master_edges(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_acoustic_join_") as temp:
            root = Path(temp)
            master = root / "master.wav"
            count = SAMPLE_RATE
            t = np.arange(count, dtype=np.float32) / SAMPLE_RATE
            samples = 0.35 * np.sin(2.0 * math.pi * 100.0 * t)
            _write_wav(master, samples.astype(np.float32))

            result = build_acoustic_join_assessments(master, [_join(start=0.4, end=0.6)])
            self.assertEqual(len(result), 1)
            item = result[0]
            self.assertEqual(item["status"], "acoustic_context_only")
            self.assertTrue(item["measurement_available"])
            self.assertEqual(item["metrics"]["sample_rate"], SAMPLE_RATE)
            self.assertFalse(item["safe_for_cut"])
            self.assertFalse(item["executable"])
            self.assertFalse(item["auto_apply"])

    def test_real_pcm_decode_detects_level_discontinuity(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_acoustic_join_") as temp:
            root = Path(temp)
            master = root / "master-level.wav"
            t = np.arange(SAMPLE_RATE, dtype=np.float32) / SAMPLE_RATE
            samples = np.zeros(SAMPLE_RATE, dtype=np.float32)
            samples[: int(0.4 * SAMPLE_RATE)] = 0.05 * np.sin(
                2.0 * math.pi * 100.0 * t[: int(0.4 * SAMPLE_RATE)]
            )
            samples[int(0.6 * SAMPLE_RATE) :] = 0.8 * np.sin(
                2.0 * math.pi * 100.0 * t[int(0.6 * SAMPLE_RATE) :]
            )
            _write_wav(master, samples)

            result = build_acoustic_join_assessments(master, [_join(start=0.4, end=0.6)])
            self.assertIn(
                result[0]["status"],
                {"level_discontinuity_risk", "combined_discontinuity_risk"},
            )
            self.assertGreater(result[0]["metrics"]["rms_delta_db"], 12.0)
            self.assertFalse(result[0]["safe_for_cut"])

    def test_audio_edge_is_insufficient(self):
        with tempfile.TemporaryDirectory(prefix="video_tunner_acoustic_join_") as temp:
            root = Path(temp)
            master = root / "short.wav"
            samples = _sine_window(seconds=0.5)
            _write_wav(master, samples)
            result = build_acoustic_join_assessments(master, [_join(start=0.02, end=0.20)])
            self.assertEqual(result[0]["status"], "insufficient_audio_context")
            self.assertFalse(result[0]["measurement_available"])


if __name__ == "__main__":
    unittest.main()
