import copy
import hashlib
import json
import unittest
from pathlib import Path

from video_tunner.denoise_treatment_human_closeout import (
    build_integrated_treatment_human_closeout,
    build_pending_integrated_review_template,
    remap_public_integrated_review_to_private,
    validate_completed_integrated_review,
    validate_integrated_bundle_technical_evidence,
)


ROOT = Path(__file__).resolve().parents[1]
PRECOMMIT_PATH = ROOT / "Validation" / "phase3-denoise-treatment-human-closeout-precommit.json"


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase3DenoiseTreatmentHumanCloseoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.precommit = json.loads(PRECOMMIT_PATH.read_text(encoding="utf-8"))
        cls.precommit_sha = sha_path(PRECOMMIT_PATH)
        cls.manifest_sha = sha_text("phase3-6k-public-manifest")
        cls.case_ids = [case["id"] for case in cls.precommit["case_selection"]["cases_in_required_order"]]
        cls.labels = cls.precommit["blinding_contract"]["treatment_label_by_case"]

    def _technical_evidence(self):
        cases = []
        for index, case_id in enumerate(self.case_ids, start=1):
            treatment = sha_text(f"treatment-{case_id}")
            preserve = sha_text(f"preserve-{case_id}")
            label = self.labels[case_id]
            frames = 480000 + index
            cases.append(
                {
                    "case_id": case_id,
                    "public_case": f"case_{index:02d}",
                    "treatment_label": label,
                    "technical_verification_sha256": sha_text(f"verification-{case_id}"),
                    "source_media_sha256": sha_text(f"source-media-{case_id}"),
                    "rendered_media_sha256": sha_text(f"rendered-media-{case_id}"),
                    "preserve_wav_sha256": preserve,
                    "treatment_wav_sha256": treatment,
                    "clean_reference_wav_sha256": sha_text(f"clean-{case_id}"),
                    "A_wav_sha256": treatment if label == "A" else preserve,
                    "B_wav_sha256": treatment if label == "B" else preserve,
                    "technical_verification": {
                        "record_type": "denoise_post_render_verification",
                        "status": "technical_denoise_pass",
                        "valid_evidence": True,
                        "technical_pass": True,
                        "human_perceptual_review_required": True,
                        "human_pass": False,
                        "blockers": [],
                        "product_default": "preserve",
                        "auto_apply": False,
                        "decoded_video_equal": True,
                        "source_frames": frames,
                        "output_frames": frames,
                    },
                }
            )
        return {
            "schema_version": 1,
            "record_type": "phase3_denoise_treatment_human_bundle_technical_evidence",
            "phase": "3.6k",
            "status": "TECHNICAL_BUNDLE_READY_FOR_HUMAN_REVIEW",
            "precommit_sha256": self.precommit_sha,
            "public_bundle_manifest_sha256": self.manifest_sha,
            "case_count": 10,
            "technical_pass_count": 10,
            "technical_fail_count": 0,
            "invalid_or_stale_count": 0,
            "cases": cases,
            "capabilities": {
                "real_guille_authorization_created": False,
                "real_guille_media_processed": False,
                "product_default": "preserve",
                "auto_apply": False,
                "stereo_or_multichannel_generalized": False,
            },
        }

    def _completed_review(self, *, treatment_preferences=10, speech_fail_index=None, artifact_fail_index=None):
        review = build_pending_integrated_review_template(
            precommit=self.precommit,
            precommit_sha256=self.precommit_sha,
            bundle_manifest_sha256=self.manifest_sha,
        )
        review["reviewer"] = "Guille"
        review["status"] = "COMPLETE"
        for index, decision in enumerate(review["decisions"]):
            case_id = decision["case_id"]
            treatment_label = self.labels[case_id]
            preserve_label = "B" if treatment_label == "A" else "A"
            decision["preference"] = treatment_label if index < treatment_preferences else preserve_label
            decision["A"] = {"speech_integrity": "PASS", "artifact": "PASS"}
            decision["B"] = {"speech_integrity": "PASS", "artifact": "PASS"}
            if index == speech_fail_index:
                decision[treatment_label]["speech_integrity"] = "FAIL"
            if index == artifact_fail_index:
                decision[treatment_label]["artifact"] = "FAIL"
            decision["reason"] = f"Auditable human reason for {case_id}."
        return review

    def test_pending_template_is_exactly_10_and_non_executable(self):
        review = build_pending_integrated_review_template(
            precommit=self.precommit,
            precommit_sha256=self.precommit_sha,
            bundle_manifest_sha256=self.manifest_sha,
        )
        self.assertEqual(review["status"], "PENDING_HUMAN_REVIEW")
        self.assertEqual(len(review["decisions"]), 10)
        self.assertEqual([item["case_id"] for item in review["decisions"]], self.case_ids)
        self.assertTrue(all(item["preference"] == "PENDING" for item in review["decisions"]))
        self.assertEqual(
            review["capabilities"],
            {
                "real_guille_authorization_created": False,
                "product_default_changed": False,
                "auto_apply": False,
                "stereo_or_multichannel_generalized": False,
            },
        )

    def test_public_review_remaps_exactly_and_duplicate_or_unknown_fails_closed(self):
        public = self._completed_review()
        for index, decision in enumerate(public["decisions"], start=1):
            decision["case_id"] = f"case_{index:02d}"
        private = remap_public_integrated_review_to_private(public_review=public, precommit=self.precommit)
        self.assertEqual([item["case_id"] for item in private["decisions"]], self.case_ids)

        duplicate = copy.deepcopy(public)
        duplicate["decisions"][1]["case_id"] = "case_01"
        with self.assertRaises(ValueError):
            remap_public_integrated_review_to_private(public_review=duplicate, precommit=self.precommit)

        unknown = copy.deepcopy(public)
        unknown["decisions"][0]["case_id"] = "case_99"
        with self.assertRaises(ValueError):
            remap_public_integrated_review_to_private(public_review=unknown, precommit=self.precommit)

    def test_technical_evidence_requires_exact_10_of_10_verified_cases(self):
        evidence = self._technical_evidence()
        result = validate_integrated_bundle_technical_evidence(
            technical_evidence=evidence,
            precommit=self.precommit,
            expected_precommit_sha256=self.precommit_sha,
        )
        self.assertTrue(result["valid"])
        self.assertEqual(result["technical_pass_count"], 10)
        self.assertEqual(result["public_bundle_manifest_sha256"], self.manifest_sha)

        failed = copy.deepcopy(evidence)
        failed["technical_pass_count"] = 9
        failed["technical_fail_count"] = 1
        with self.assertRaises(ValueError):
            validate_integrated_bundle_technical_evidence(
                technical_evidence=failed,
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
            )

        stale = copy.deepcopy(evidence)
        stale["cases"][0]["technical_verification"]["valid_evidence"] = False
        with self.assertRaises(ValueError):
            validate_integrated_bundle_technical_evidence(
                technical_evidence=stale,
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
            )

    def test_completed_review_rejects_pending_missing_reason_and_capability_tamper(self):
        pending = build_pending_integrated_review_template(
            precommit=self.precommit,
            precommit_sha256=self.precommit_sha,
            bundle_manifest_sha256=self.manifest_sha,
        )
        with self.assertRaises(ValueError):
            validate_completed_integrated_review(
                review=pending,
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
                expected_bundle_manifest_sha256=self.manifest_sha,
            )

        missing_reason = self._completed_review()
        missing_reason["decisions"][0]["reason"] = ""
        with self.assertRaises(ValueError):
            validate_completed_integrated_review(
                review=missing_reason,
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
                expected_bundle_manifest_sha256=self.manifest_sha,
            )

        tampered = self._completed_review()
        tampered["capabilities"]["auto_apply"] = True
        with self.assertRaises(ValueError):
            validate_completed_integrated_review(
                review=tampered,
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
                expected_bundle_manifest_sha256=self.manifest_sha,
            )

    def test_exact_reused_gate_passes_at_7_of_10_without_failures(self):
        closeout = build_integrated_treatment_human_closeout(
            review=self._completed_review(treatment_preferences=7),
            technical_evidence=self._technical_evidence(),
            precommit=self.precommit,
            expected_precommit_sha256=self.precommit_sha,
            technical_evidence_sha256=sha_text("technical-evidence"),
        )
        self.assertEqual(closeout["status"], "HUMAN_TREATMENT_CLOSEOUT_READY")
        self.assertEqual(closeout["results"]["integrated_treatment_preferences"], 7)
        self.assertEqual(closeout["results"]["preserve_preferences"], 3)
        self.assertTrue(closeout["results"]["human_gate_pass"])
        self.assertEqual(closeout["interpretation"]["product_default"], "preserve")
        self.assertFalse(closeout["interpretation"]["auto_apply"])
        self.assertFalse(closeout["interpretation"]["real_guille_authorization_created"])

    def test_six_of_ten_preferences_fails_without_threshold_relaxation(self):
        closeout = build_integrated_treatment_human_closeout(
            review=self._completed_review(treatment_preferences=6),
            technical_evidence=self._technical_evidence(),
            precommit=self.precommit,
            expected_precommit_sha256=self.precommit_sha,
            technical_evidence_sha256=sha_text("technical-evidence"),
        )
        self.assertEqual(closeout["status"], "INSUFFICIENT_INTEGRATED_TREATMENT_QUALITY")
        self.assertFalse(closeout["results"]["human_gate_pass"])
        self.assertTrue(closeout["interpretation"]["failure_keeps_phase_open"])
        self.assertFalse(closeout["interpretation"]["thresholds_relaxed_post_hoc"])

    def test_one_treatment_speech_integrity_failure_vetoes_closeout(self):
        closeout = build_integrated_treatment_human_closeout(
            review=self._completed_review(treatment_preferences=10, speech_fail_index=0),
            technical_evidence=self._technical_evidence(),
            precommit=self.precommit,
            expected_precommit_sha256=self.precommit_sha,
            technical_evidence_sha256=sha_text("technical-evidence"),
        )
        self.assertEqual(closeout["status"], "INSUFFICIENT_INTEGRATED_TREATMENT_QUALITY")
        self.assertEqual(closeout["results"]["integrated_treatment_speech_integrity_failures"], 1)

    def test_one_treatment_artifact_failure_vetoes_closeout(self):
        closeout = build_integrated_treatment_human_closeout(
            review=self._completed_review(treatment_preferences=10, artifact_fail_index=0),
            technical_evidence=self._technical_evidence(),
            precommit=self.precommit,
            expected_precommit_sha256=self.precommit_sha,
            technical_evidence_sha256=sha_text("technical-evidence"),
        )
        self.assertEqual(closeout["status"], "INSUFFICIENT_INTEGRATED_TREATMENT_QUALITY")
        self.assertEqual(closeout["results"]["integrated_treatment_artifact_failures"], 1)

    def test_stale_bundle_or_precommit_hash_cannot_be_closed(self):
        review = self._completed_review()
        review["bundle_manifest_sha256"] = sha_text("wrong-manifest")
        with self.assertRaises(ValueError):
            build_integrated_treatment_human_closeout(
                review=review,
                technical_evidence=self._technical_evidence(),
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
                technical_evidence_sha256=sha_text("technical-evidence"),
            )

        evidence = self._technical_evidence()
        evidence["precommit_sha256"] = sha_text("wrong-precommit")
        with self.assertRaises(ValueError):
            build_integrated_treatment_human_closeout(
                review=self._completed_review(),
                technical_evidence=evidence,
                precommit=self.precommit,
                expected_precommit_sha256=self.precommit_sha,
                technical_evidence_sha256=sha_text("technical-evidence"),
            )


if __name__ == "__main__":
    unittest.main()
