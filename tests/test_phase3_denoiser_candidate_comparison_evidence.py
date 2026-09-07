import hashlib
import json
import math
import statistics
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "tests" / "fixtures" / "phase3_denoise_evaluation_corpus_v1.json"
METRICS = ROOT / "tests" / "fixtures" / "phase3_denoise_objective_metric_policy_v1.json"
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_candidate_comparison_policy_v1.json"
MATERIALIZATION = ROOT / "Validation" / "phase3-denoise-corpus-materialization.json"
BASELINE = ROOT / "Validation" / "phase3-denoise-objective-baseline.json"
EVIDENCE = ROOT / "Validation" / "phase3-denoiser-candidate-objective-comparison.json"

RAW_COMPARISON_SHA = "0b1215fcd26b709ce3c8d232a2144b74c70e3dc13ec3bd7ab706793948d37023"
ARTIFACT_DIGEST = "sha256:db8202040779a74351e3c1f1a8766245916924deb37ae727c93f3782cb8df9b8"
RUN_HEAD_SHA = "1c181220f78acec62250ce724834a0073daeec39"
DF_SHA = "75e11fa16445f560cb6b021521ddb89e89270d13b83089705d98776f58fd7915"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mean(values):
    return round(statistics.fmean(values), 8)


class Phase3DenoiserCandidateComparisonEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        cls.corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        cls.baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
        cls.expected_ids = {case["id"] for case in cls.corpus["cases"]}

    def test_provenance_is_exactly_bound_to_successful_run_and_raw_artifact(self):
        p = self.evidence["provenance"]
        self.assertEqual(p["workflow_run_id"], 34145308485)
        self.assertEqual(p["workflow_job_id"], 101815955163)
        self.assertEqual(p["run_head_sha"], RUN_HEAD_SHA)
        self.assertEqual(p["artifact_id"], 10027581922)
        self.assertEqual(p["artifact_name"], "phase3-denoiser-candidate-objective-comparison")
        self.assertEqual(p["artifact_digest"], ARTIFACT_DIGEST)
        self.assertEqual(p["raw_comparison_json_sha256"], RAW_COMPARISON_SHA)
        self.assertEqual(p["raw_comparison_json_size_bytes"], 264619)

    def test_frozen_inputs_match_current_exact_repository_evidence(self):
        bindings = self.evidence["bindings"]
        self.assertEqual(bindings["candidate_policy_sha256"], sha(POLICY))
        self.assertEqual(bindings["corpus_fixture_sha256"], sha(CORPUS))
        self.assertEqual(bindings["metric_policy_sha256"], sha(METRICS))
        self.assertEqual(bindings["materialization_evidence_sha256"], sha(MATERIALIZATION))
        self.assertEqual(bindings["baseline_evidence_sha256"], sha(BASELINE))
        self.assertEqual(bindings["raw_noisy_baseline_sha256"], "0c11cf701618d461cd1144a817edc77f75225333b306f91310a972475cb183fe")

    def test_exact_three_candidate_set_and_all_required_cases_are_present(self):
        results = self.evidence["results"]
        self.assertEqual(
            set(results),
            {"preserve_noisy_control_v1", "ffmpeg_afftdn_fixed_v1", "deepfilternet_0_5_6_compensated_v1"},
        )
        self.assertEqual(self.evidence["candidate_count"], 3)
        self.assertEqual(self.evidence["required_noisy_cases_per_candidate"], 40)
        self.assertEqual(self.evidence["required_clean_controls_per_treatment_candidate"], 40)
        for candidate_id, result in results.items():
            noisy = result["noisy_cases"]
            self.assertEqual(len(noisy), 40, candidate_id)
            self.assertEqual({case["id"] for case in noisy}, self.expected_ids, candidate_id)
            if candidate_id == "preserve_noisy_control_v1":
                self.assertFalse(result["clean_control"]["required"])
            else:
                clean = result["clean_control"]["cases"]
                self.assertEqual(len(clean), 40, candidate_id)
                self.assertEqual({case["id"] for case in clean}, self.expected_ids, candidate_id)

    def test_preserve_arm_is_exact_baseline_identity(self):
        baseline_by_id = {case["id"]: case for case in self.baseline["cases"]}
        preserve = self.evidence["results"]["preserve_noisy_control_v1"]["noisy_cases"]
        for case in preserve:
            base = baseline_by_id[case["id"]]
            self.assertEqual(case["metrics"], base["metrics"])
            self.assertEqual(case["input_noisy_sha256"], base["noisy_sha256"])
            self.assertEqual(case["output_sha256"], base["noisy_sha256"])
            self.assertEqual(case["delta_vs_preserve"], {"si_sdr_db": 0.0, "stoi": 0.0})

    def test_timeline_normalization_never_hides_more_than_precommitted_50ms(self):
        for candidate_id in ("ffmpeg_afftdn_fixed_v1", "deepfilternet_0_5_6_compensated_v1"):
            result = self.evidence["results"][candidate_id]
            for case in result["noisy_cases"] + result["clean_control"]["cases"]:
                timeline = case["timeline"]
                self.assertLessEqual(abs(timeline["raw_duration_delta_seconds"]), 0.05 + 1e-12)
                self.assertFalse(timeline["alignment_search_performed"])
                self.assertFalse(timeline["time_shift_performed"])
                self.assertFalse(timeline["level_matching_performed"])
                self.assertIn(timeline["action"], {"none", "right_pad", "right_trim"})
        df = self.evidence["results"]["deepfilternet_0_5_6_compensated_v1"]
        self.assertTrue(all(case["timeline"]["raw_duration_delta_seconds"] == -0.03 for case in df["noisy_cases"]))
        self.assertTrue(all(case["timeline"]["raw_duration_delta_seconds"] == -0.03 for case in df["clean_control"]["cases"]))

    def test_output_hashes_and_pinned_deepfilternet_identity_are_auditable(self):
        runtime = self.evidence["runtime"]["deepfilternet"]
        self.assertEqual(runtime["asset_sha256"], DF_SHA)
        self.assertEqual(runtime["asset_size_bytes"], 26912256)
        for candidate_id in ("ffmpeg_afftdn_fixed_v1", "deepfilternet_0_5_6_compensated_v1"):
            result = self.evidence["results"][candidate_id]
            for case in result["noisy_cases"] + result["clean_control"]["cases"]:
                for key in ("raw_output_sha256", "metric_pcm16_sha256"):
                    value = case[key]
                    self.assertEqual(len(value), 64)
                    int(value, 16)

    def test_aggregates_recompute_from_all_40_cases_without_exclusion(self):
        for candidate_id, result in self.evidence["results"].items():
            cases = result["noisy_cases"]
            overall = result["noisy_summary"]["overall"]
            self.assertEqual(overall["case_count"], 40)
            self.assertEqual(overall["si_sdr_db"]["mean"], mean([c["metrics"]["si_sdr_db"] for c in cases]))
            self.assertEqual(overall["stoi"]["mean"], mean([c["metrics"]["stoi"] for c in cases]))
            self.assertEqual(
                overall["delta_vs_preserve"]["si_sdr_db"]["mean"],
                mean([c["delta_vs_preserve"]["si_sdr_db"] for c in cases]),
            )
            self.assertEqual(
                overall["delta_vs_preserve"]["stoi"]["mean"],
                mean([c["delta_vs_preserve"]["stoi"] for c in cases]),
            )
            if result["clean_control"].get("required"):
                clean = result["clean_control"]["cases"]
                summary = result["clean_control"]["summary"]
                self.assertEqual(summary["case_count"], 40)
                self.assertEqual(summary["stoi"]["mean"], mean([c["metrics"]["stoi"] for c in clean]))
                self.assertEqual(
                    summary["normalized_rmse"]["mean"],
                    mean([c["metrics"]["normalized_rmse"] for c in clean]),
                )

    def test_observed_descriptive_results_are_frozen_without_declaring_winner(self):
        results = self.evidence["results"]
        preserve = results["preserve_noisy_control_v1"]["noisy_summary"]["overall"]
        afftdn = results["ffmpeg_afftdn_fixed_v1"]["noisy_summary"]["overall"]
        df = results["deepfilternet_0_5_6_compensated_v1"]["noisy_summary"]["overall"]
        self.assertEqual((preserve["si_sdr_db"]["mean"], preserve["stoi"]["mean"]), (9.16548156, 0.95070362))
        self.assertEqual((afftdn["si_sdr_db"]["mean"], afftdn["stoi"]["mean"]), (-31.01735476, 0.54563814))
        self.assertEqual((df["si_sdr_db"]["mean"], df["stoi"]["mean"]), (19.03561569, 0.96183329))
        self.assertEqual(results["ffmpeg_afftdn_fixed_v1"]["clean_control"]["summary"]["stoi"]["mean"], 0.5527063)
        self.assertEqual(results["ffmpeg_afftdn_fixed_v1"]["clean_control"]["summary"]["normalized_rmse"]["mean"], 1.41255832)
        self.assertEqual(results["deepfilternet_0_5_6_compensated_v1"]["clean_control"]["summary"]["stoi"]["mean"], 0.99542798)
        self.assertEqual(results["deepfilternet_0_5_6_compensated_v1"]["clean_control"]["summary"]["normalized_rmse"]["mean"], 0.03238068)

        aff_cases = results["ffmpeg_afftdn_fixed_v1"]["noisy_cases"]
        df_cases = results["deepfilternet_0_5_6_compensated_v1"]["noisy_cases"]
        self.assertEqual(sum(c["delta_vs_preserve"]["si_sdr_db"] > 0 for c in aff_cases), 0)
        self.assertEqual(sum(c["delta_vs_preserve"]["stoi"] > 0 for c in aff_cases), 0)
        self.assertEqual(sum(c["delta_vs_preserve"]["si_sdr_db"] > 0 for c in df_cases), 40)
        self.assertEqual(sum(c["delta_vs_preserve"]["stoi"] > 0 for c in df_cases), 27)
        self.assertEqual(sum(c["delta_vs_preserve"]["stoi"] < 0 for c in df_cases), 13)

    def test_objective_evidence_has_zero_selection_or_execution_capability(self):
        interpretation = self.evidence["interpretation"]
        self.assertTrue(interpretation["descriptive_objective_comparison_only"])
        self.assertTrue(interpretation["objective_metrics_are_auxiliary_only"])
        self.assertIsNone(interpretation["winner_label"])
        self.assertFalse(interpretation["acceptance_thresholds_defined"])
        self.assertFalse(interpretation["candidate_selection_authorized"])
        self.assertFalse(interpretation["denoiser_selected"])
        self.assertFalse(interpretation["denoise_authorized"])
        self.assertFalse(interpretation["renderer_authorized"])
        self.assertTrue(interpretation["human_perceptual_ab_required_before_any_selection_or_authorization"])
        self.assertFalse(interpretation["auto_apply"])


if __name__ == "__main__":
    unittest.main()
