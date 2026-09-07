from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from video_tunner.denoise_selection import build_denoiser_selection_review


ROOT = Path(__file__).resolve().parents[1]
OBJECTIVE = ROOT / "Validation" / "phase3-denoiser-candidate-objective-comparison.json"
HUMAN = ROOT / "Validation" / "phase3-denoiser-human-perceptual-gate.json"
POLICY = ROOT / "tests" / "fixtures" / "phase3_denoiser_selection_policy_v1.json"
EVIDENCE = ROOT / "Validation" / "phase3-denoiser-selection-review.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Phase3DenoiserSelectionReviewEvidenceTests(unittest.TestCase):
    def test_persisted_selection_exactly_recomputes_from_frozen_inputs(self):
        objective = load(OBJECTIVE)
        human = load(HUMAN)
        policy = load(POLICY)
        persisted = load(EVIDENCE)
        provenance = persisted.pop("provenance")

        recomputed = build_denoiser_selection_review(
            objective_evidence=objective,
            human_gate=human,
            policy=policy,
        )
        self.assertEqual(persisted, recomputed)
        self.assertEqual(provenance["evidence_source"], "github_actions_artifact")

    def test_selection_provenance_is_exact_successful_artifact(self):
        evidence = load(EVIDENCE)
        provenance = evidence["provenance"]
        self.assertEqual(provenance["workflow_run_id"], 34150663772)
        self.assertEqual(provenance["workflow_job_id"], 101832099685)
        self.assertEqual(provenance["run_head_sha"], "f07d7b195af1c27c94cb8fba7e267fc20fb19a50")
        self.assertEqual(provenance["artifact_id"], 10029234401)
        self.assertEqual(provenance["artifact_name"], "phase3-denoiser-selection-review")
        self.assertEqual(
            provenance["artifact_digest"],
            "sha256:0d55e6b9246d6a510639a6c7dd934d132928774f4836181d611a1bcf935dcddc",
        )
        self.assertEqual(provenance["artifact_zip_sha256"], "0d55e6b9246d6a510639a6c7dd934d132928774f4836181d611a1bcf935dcddc")
        self.assertEqual(provenance["raw_selection_json_sha256"], "2c9595994d3210bd963c3601832ad46707a4c106a0f0cf97bc713bf97143c539")
        self.assertEqual(provenance["raw_selection_json_size_bytes"], 1482)

    def test_persisted_selection_is_non_executable_and_preserve_stays_default(self):
        evidence = load(EVIDENCE)
        self.assertEqual(evidence["status"], "SELECTED_FOR_INTEGRATION_REVIEW")
        self.assertEqual(evidence["selected_candidate_id"], "deepfilternet_0_5_6_compensated_v1")
        interpretation = evidence["interpretation"]
        self.assertTrue(interpretation["selected_candidate_is_for_integration_review_only"])
        self.assertEqual(interpretation["product_default"], "preserve")
        self.assertFalse(interpretation["product_default_changed"])
        self.assertFalse(interpretation["denoise_authorized"])
        self.assertFalse(interpretation["renderer_authorized"])
        self.assertFalse(interpretation["auto_apply"])


if __name__ == "__main__":
    unittest.main()
