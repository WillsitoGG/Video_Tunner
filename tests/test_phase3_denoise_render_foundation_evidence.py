import json
import unittest
from pathlib import Path

from video_tunner.denoise_render import (
    DENOISE_RENDER_AUDIO_BITRATE,
    DENOISE_RENDER_AUDIO_CODEC,
    DENOISE_RENDER_RECORD_TYPE,
    DENOISE_RENDER_SCHEMA_VERSION,
)
from video_tunner.denoise_runtime import (
    DEEPFILTER_ARGUMENTS,
    DEEPFILTER_ASSET_SHA256,
    DEEPFILTER_ASSET_SIZE_BYTES,
    DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
    DEEPFILTER_RUNTIME_RELATIVE_PATH,
    DEEPFILTER_VERSION,
    SELECTED_DENOISER_ID,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "Validation" / "phase3-denoise-render-foundation.json"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "phase3-denoise-render-foundation.yml"


class Phase3DenoiseRenderFoundationEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))

    def test_foundation_identity_and_successful_validation_are_frozen(self):
        evidence = self.evidence
        self.assertEqual(evidence["schema_version"], 1)
        self.assertEqual(evidence["record_type"], "phase3_denoise_render_foundation")
        self.assertEqual(evidence["phase"], "3.6i")
        self.assertEqual(evidence["status"], "TECHNICAL_FOUNDATION_PASS")
        validation = evidence["validation"]
        self.assertEqual(validation["run_id"], 34231340544)
        self.assertEqual(validation["job_id"], 102077969922)
        self.assertEqual(validation["head_sha"], "f4f881012132087319de2f4a6b1ed6519e26db90")
        self.assertEqual(validation["focused_tests"], "49/49 PASS")
        self.assertEqual(validation["deepfilter_real_synthetic_e2e"], "1/1 PASS")
        self.assertEqual(validation["integrated_tests"], "466/466 PASS")
        self.assertEqual(validation["integrated_skips"], 0)
        self.assertEqual(validation["doctor"], "PASS")
        self.assertTrue(validation["scope_note_pass"])

    def test_persisted_renderer_and_runtime_contract_match_implementation_constants(self):
        implementation = self.evidence["implementation"]
        self.assertEqual(implementation["render_schema_version"], DENOISE_RENDER_SCHEMA_VERSION)
        self.assertEqual(implementation["render_record_type"], DENOISE_RENDER_RECORD_TYPE)
        self.assertEqual(implementation["selected_candidate_id"], SELECTED_DENOISER_ID)
        self.assertEqual(implementation["deepfilter_version"], DEEPFILTER_VERSION)
        self.assertEqual(implementation["deepfilter_asset_sha256"], DEEPFILTER_ASSET_SHA256)
        self.assertEqual(implementation["deepfilter_asset_size_bytes"], DEEPFILTER_ASSET_SIZE_BYTES)
        self.assertEqual(implementation["runtime_relative_path"], DEEPFILTER_RUNTIME_RELATIVE_PATH.as_posix())
        self.assertEqual(implementation["arguments_template"], DEEPFILTER_ARGUMENTS)
        self.assertEqual(implementation["render_audio_codec"], DENOISE_RENDER_AUDIO_CODEC)
        self.assertEqual(implementation["render_audio_bitrate"], DENOISE_RENDER_AUDIO_BITRATE)
        self.assertEqual(implementation["video_mode"], "stream_copy")

    def test_execution_gate_and_timeline_policy_are_persisted_fail_closed(self):
        gate = self.evidence["execution_gate"]
        for key in (
            "complete_phase3_6a_to_3_6h_chain_revalidated_immediately_before_processing",
            "current_source_sha256_required",
            "explicit_per_media_execution_authorization_required",
            "selected_runtime_sha_size_and_cli_revalidated",
            "deepfilter_cli_materialized_from_validated_plan_template",
            "tampered_or_extended_cli_template_fails_closed",
            "source_overwrite_forbidden",
            "exactly_one_video_stream_required",
            "exactly_one_audio_stream_required",
            "initial_foundation_requires_mono_source_audio",
            "stereo_or_multichannel_fails_closed",
            "delay_compensation_required",
        ):
            self.assertTrue(gate[key])
        self.assertEqual(gate["input_pcm"], "pcm_s16le")
        self.assertEqual(gate["input_channels"], 1)
        self.assertEqual(gate["input_sample_rate_hz"], 48000)
        self.assertEqual(gate["raw_duration_delta_max_seconds"], DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS)
        self.assertFalse(gate["alignment_search_allowed"])
        self.assertFalse(gate["time_shift_allowed"])
        self.assertFalse(gate["level_matching_allowed"])
        self.assertEqual(
            gate["timeline_normalization_allowed"],
            "right_tail_trim_or_digital_silence_pad_only",
        )

    def test_observed_synthetic_timeline_is_exact_and_inside_precommitted_limit(self):
        observed = self.evidence["synthetic_e2e_observation"]
        self.assertFalse(observed["real_user_media"])
        self.assertTrue(observed["deepfilter_real_binary_executed"])
        self.assertEqual(observed["input_frames"], 144000)
        self.assertEqual(observed["raw_output_frames"], 142560)
        self.assertEqual(observed["raw_frame_delta"], -1440)
        self.assertEqual(observed["raw_duration_delta_seconds"], -0.03)
        self.assertLessEqual(
            abs(observed["raw_duration_delta_seconds"]),
            DEEPFILTER_RAW_DURATION_DELTA_MAX_SECONDS,
        )
        self.assertEqual(observed["timeline_normalization_action"], "pad_right_tail_silence")
        self.assertEqual(observed["final_frames"], observed["input_frames"])
        self.assertFalse(observed["alignment_search_performed"])
        self.assertFalse(observed["time_shift_performed"])
        self.assertFalse(observed["level_matching_performed"])

    def test_render_complete_cannot_be_misread_as_quality_or_human_pass(self):
        contract = self.evidence["render_contract"]
        self.assertTrue(contract["video_stream_copy_required"])
        self.assertEqual(contract["audio_codec"], "aac")
        self.assertEqual(contract["audio_bitrate"], "192k")
        self.assertFalse(contract["shortest_flag_allowed"])
        self.assertTrue(contract["source_sha_rechecked_after_render"])
        self.assertFalse(contract["render_complete_is_technical_pass"])
        self.assertFalse(contract["render_complete_is_human_pass"])
        self.assertTrue(contract["technical_post_render_verification_required"])
        self.assertTrue(contract["human_perceptual_review_required"])
        self.assertEqual(contract["product_default"], "preserve")
        self.assertFalse(contract["product_default_changed"])
        self.assertFalse(contract["auto_apply"])

    def test_actual_product_state_records_no_real_user_authorization_or_processing(self):
        state = self.evidence["actual_product_state"]
        self.assertTrue(state["denoise_renderer_technical_foundation_implemented"])
        self.assertFalse(state["denoise_renderer_generalized_to_stereo_or_multichannel"])
        self.assertFalse(state["independent_denoise_post_render_verifier_implemented"])
        self.assertFalse(state["real_user_authorization_record_created"])
        self.assertFalse(state["real_user_media_authorized_for_denoise"])
        self.assertFalse(state["real_user_media_processed_by_denoise_renderer"])
        self.assertFalse(state["real_user_treated_media_generated"])
        self.assertEqual(state["product_default"], "preserve")
        self.assertFalse(state["product_default_changed"])
        self.assertFalse(state["auto_apply"])
        interpretation = self.evidence["interpretation"]
        self.assertTrue(interpretation["phase3_6i_technical_foundation_closed"])
        self.assertTrue(interpretation["synthetic_approve_path_only"])
        self.assertTrue(interpretation["guille_did_not_issue_a_real_per_media_denoise_authorization_in_3_6i"])
        self.assertEqual(
            interpretation["next_phase"],
            "3.6j_independent_denoise_post_render_technical_verifier",
        )

    def test_permanent_gate_is_manual_only_and_includes_persisted_3_6i_binder(self):
        workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)
        self.assertIn("tests.test_phase3_denoise_render_foundation_evidence", workflow)
        self.assertIn("No Guille media is processed or authorized", workflow)
        self.assertIn("Render complete is not technical PASS or human PASS", workflow)

    def test_master_docs_are_synchronized_to_3_6i_closed_and_3_6j_next(self):
        docs = {
            "README": (ROOT / "README.md").read_text(encoding="utf-8"),
            "AGENTS": (ROOT / "AGENTS.md").read_text(encoding="utf-8"),
            "ROADMAP": (ROOT / "ROADMAP.md").read_text(encoding="utf-8"),
            "RELEASE_STATUS": (ROOT / "RELEASE_STATUS.md").read_text(encoding="utf-8"),
            "VALIDATION_README": (ROOT / "Validation" / "README.md").read_text(encoding="utf-8"),
        }
        for name, content in docs.items():
            with self.subTest(document=name):
                self.assertIn("3.6i", content)
                self.assertIn("3.6j", content)
        self.assertIn("Fase 3.6i — Gated Denoise Renderer: ✅ **TECHNICAL FOUNDATION PASS**", docs["README"])
        self.assertIn("Siguiente trabajo — Fase 3.6j", docs["README"])
        self.assertIn("3.6i — gated denoise renderer technical foundation", docs["AGENTS"])
        self.assertIn("3.6j independent denoise post-render technical verifier", docs["AGENTS"])
        self.assertIn("3.6i — Gated Denoise Renderer Technical Foundation — COMPLETADA", docs["ROADMAP"])
        self.assertIn("3.6j — Independent Denoise Post-Render Technical Verifier — SIGUIENTE", docs["ROADMAP"])
        self.assertIn("Fase 3.6i: **TECHNICAL FOUNDATION PASS", docs["RELEASE_STATUS"])
        self.assertIn("phase3-denoise-render-foundation.json", docs["VALIDATION_README"])
        self.assertIn("real_user_media_processed_by_denoise_renderer = false", docs["VALIDATION_README"])


if __name__ == "__main__":
    unittest.main()
