import hashlib
import itertools
import json
import unittest
from pathlib import Path


FIXTURE = Path(__file__).parent / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"


class Phase3DenoiseEvaluationCorpusFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_non_executable_and_does_not_select_denoiser(self):
        payload = self.payload
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["record_type"], "denoise_evaluation_corpus_fixture")
        policy = payload["evaluation_policy"]
        self.assertTrue(policy["clean_reference_required"])
        self.assertTrue(policy["objective_metrics_are_auxiliary_only"])
        self.assertTrue(policy["human_perceptual_comparison_required_before_treatment_authorization"])
        self.assertFalse(policy["denoiser_selected"])
        self.assertFalse(policy["denoise_authorized"])
        self.assertFalse(policy["renderer_authorized"])
        self.assertFalse(policy["auto_apply"])

    def test_dataset_provenance_and_official_archive_checksums_are_frozen(self):
        dataset = self.payload["dataset"]
        self.assertEqual(dataset["persistent_identifier"], "https://doi.org/10.7488/ds/2117")
        self.assertEqual(dataset["license"], "Creative Commons Attribution 4.0 International Public License")
        self.assertEqual(dataset["native_sample_rate_hz"], 48000)
        expected = {
            "clean_testset": ("clean_testset_wav.zip", "34eb1c0ba7ef667e9b966866c542fc16"),
            "noisy_testset": ("noisy_testset_wav.zip", "fb1b86caa31e8ba5b506c0c64da9aab5"),
            "logfiles": ("logfiles.zip", "0d16f5b6afe12d64238d1e4a0e6ff6e8"),
        }
        for key, (filename, md5) in expected.items():
            archive = self.payload["archives"][key]
            self.assertEqual(archive["filename"], filename)
            self.assertEqual(archive["md5"], md5)
            self.assertEqual(len(md5), 32)
            int(md5, 16)

    def test_selection_is_exact_full_factorial_with_no_duplicates(self):
        payload = self.payload
        cases = payload["cases"]
        selection = payload["selection_policy"]
        self.assertTrue(selection["selection_frozen_before_algorithm_comparison"])
        self.assertFalse(selection["algorithm_results_used_for_selection"])
        self.assertFalse(selection["human_preferences_used_for_selection"])
        self.assertEqual(selection["required_cases"], 40)
        self.assertEqual(len(cases), 40)
        self.assertEqual(len({case["id"] for case in cases}), 40)

        expected_cells = set(
            itertools.product(
                self.payload["dataset"]["test_set"]["speakers"],
                self.payload["dataset"]["test_set"]["noise_types"],
                self.payload["dataset"]["test_set"]["snr_db"],
            )
        )
        actual_cells = {
            (case["speaker"], case["noise"], float(case["snr_db"]))
            for case in cases
        }
        self.assertEqual(actual_cells, expected_cells)

    def test_case_ids_match_their_speaker_and_are_safe_basenames(self):
        for case in self.payload["cases"]:
            case_id = case["id"]
            self.assertTrue(case_id.startswith(case["speaker"] + "_"))
            self.assertNotIn("/", case_id)
            self.assertNotIn("\\", case_id)
            self.assertEqual(Path(case_id).name, case_id)

    def test_fixture_bytes_have_stable_sha256_shape_for_downstream_binding(self):
        digest = hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)
        int(digest, 16)


if __name__ == "__main__":
    unittest.main()
