from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner import denoise_runtime


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_candidate_comparison_policy_v1.json"
SELECTION = ROOT / "Validation" / "phase3-denoiser-selection-review.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class DenoiseRuntimeContractTests(unittest.TestCase):
    def test_contract_matches_frozen_candidate_policy_exactly(self):
        policy = load(CANDIDATE_POLICY)
        frozen = next(
            candidate
            for candidate in policy["candidates"]
            if candidate["id"] == "deepfilternet_0_5_6_compensated_v1"
        )
        contract = denoise_runtime.selected_denoiser_contract()

        self.assertEqual(contract["candidate_id"], frozen["id"])
        self.assertEqual(contract["implementation"], frozen["implementation"])
        self.assertEqual(contract["version"], frozen["version"])
        self.assertEqual(contract["asset_url"], frozen["asset_url"])
        self.assertEqual(contract["asset_sha256"], frozen["asset_sha256"])
        self.assertEqual(contract["asset_size_bytes"], frozen["asset_size_bytes"])
        self.assertEqual(contract["arguments"], frozen["arguments"])
        self.assertEqual(contract["explicit_model_argument"], frozen["explicit_model_argument"])
        self.assertEqual(contract["media_contract"]["input_pcm"], policy["media_contract"]["input_pcm"])
        self.assertEqual(contract["media_contract"]["input_channels"], policy["media_contract"]["input_channels"])
        self.assertEqual(
            contract["media_contract"]["input_sample_rate_hz"],
            policy["media_contract"]["input_sample_rate_hz"],
        )
        self.assertEqual(
            contract["media_contract"]["output_channels"],
            policy["media_contract"]["candidate_output_channels"],
        )
        self.assertEqual(
            contract["media_contract"]["output_sample_rate_hz"],
            policy["media_contract"]["candidate_output_sample_rate_hz"],
        )
        self.assertEqual(
            contract["media_contract"]["raw_duration_delta_max_seconds"],
            policy["media_contract"]["raw_duration_delta_max_seconds"],
        )

    def test_contract_matches_selected_candidate_and_remains_non_executable(self):
        selection = load(SELECTION)
        contract = denoise_runtime.selected_denoiser_contract()
        state = contract["integration_state"]

        self.assertEqual(contract["candidate_id"], selection["selected_candidate_id"])
        self.assertTrue(state["selected_for_integration_review_only"])
        self.assertFalse(state["runtime_download_allowed"])
        self.assertEqual(state["product_default"], "preserve")
        self.assertFalse(state["denoise_authorized"])
        self.assertFalse(state["renderer_authorized"])
        self.assertFalse(state["auto_apply"])

    def test_runtime_path_is_fixed_inside_portable_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(
                denoise_runtime.deepfilter_executable_path(root),
                root.resolve() / "Tools" / "deepfilter" / "bin" / "deep-filter.exe",
            )

    def test_missing_binary_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "deep-filter.exe"
            with self.assertRaises(denoise_runtime.DenoiserRuntimeError):
                denoise_runtime.validate_selected_denoiser_binary(missing)

    def test_size_mismatch_fails_closed_before_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "deep-filter.exe"
            binary.write_bytes(b"wrong")
            with self.assertRaisesRegex(denoise_runtime.DenoiserRuntimeError, "size mismatch"):
                denoise_runtime.validate_selected_denoiser_binary(binary)

    def test_hash_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "deep-filter.exe"
            binary.write_bytes(b"abc")
            with (
                patch.object(denoise_runtime, "DEEPFILTER_ASSET_SIZE_BYTES", 3),
                patch.object(denoise_runtime, "DEEPFILTER_ASSET_SHA256", "0" * 64),
            ):
                with self.assertRaisesRegex(denoise_runtime.DenoiserRuntimeError, "SHA256 mismatch"):
                    denoise_runtime.validate_selected_denoiser_binary(binary)

    def test_valid_binary_contract_can_probe_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "deep-filter.exe"
            payload = b"abc"
            binary.write_bytes(payload)
            expected_sha = hashlib.sha256(payload).hexdigest()

            def probe(_executable: Path, argument: str) -> str:
                if argument == "--version":
                    return "deep-filter 0.5.6"
                if argument == "--help":
                    return "Usage: deep-filter --compensate-delay --output-dir <DIR> <INPUT>"
                raise AssertionError(argument)

            with (
                patch.object(denoise_runtime, "DEEPFILTER_ASSET_SIZE_BYTES", len(payload)),
                patch.object(denoise_runtime, "DEEPFILTER_ASSET_SHA256", expected_sha),
                patch.object(denoise_runtime, "_run_probe", side_effect=probe),
            ):
                result = denoise_runtime.validate_selected_denoiser_binary(binary, probe_cli=True)

            self.assertTrue(result["valid"])
            self.assertTrue(result["cli_contract_pass"])
            self.assertFalse(result["runtime_download_allowed"])
            self.assertFalse(result["denoise_authorized"])
            self.assertFalse(result["renderer_authorized"])
            self.assertFalse(result["auto_apply"])

    def test_cli_probe_fails_closed_when_required_flag_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            binary = Path(temp) / "deep-filter.exe"
            payload = b"abc"
            binary.write_bytes(payload)
            expected_sha = hashlib.sha256(payload).hexdigest()

            def probe(_executable: Path, argument: str) -> str:
                return "deep-filter 0.5.6" if argument == "--version" else "Usage: deep-filter <INPUT>"

            with (
                patch.object(denoise_runtime, "DEEPFILTER_ASSET_SIZE_BYTES", len(payload)),
                patch.object(denoise_runtime, "DEEPFILTER_ASSET_SHA256", expected_sha),
                patch.object(denoise_runtime, "_run_probe", side_effect=probe),
            ):
                with self.assertRaisesRegex(denoise_runtime.DenoiserRuntimeError, "CLI contract"):
                    denoise_runtime.validate_selected_denoiser_binary(binary, probe_cli=True)


if __name__ == "__main__":
    unittest.main()
