import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "finalize_phase2e_human_closeout.py"
SPEC = importlib.util.spec_from_file_location("phase2e_human_closeout_finalizer", SCRIPT_PATH)
assert SPEC and SPEC.loader
FINALIZER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FINALIZER)


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def technical_report(index: int) -> dict:
    return {
        "schema_version": 1,
        "record_type": "semantic_render_verification",
        "status": "technical_post_render_pass",
        "technical_pass": True,
        "blockers": [],
        "execution_chain": {"plan_fingerprint": f"{index + 3:x}" * 64},
        "output": {"sha256": f"{index + 6:x}" * 64},
        "post_render_join_audits": [
            {
                "id": "post-render-join-0001",
                "edit_id": "semantic-edit-0001",
                "candidate_id": f"candidate-{index}",
                "output_join_seconds": float(index),
                "status": "acoustic_context_only",
                "technical_pass": True,
            }
        ],
        "auto_apply": False,
    }


def decisions(case_ids: list[str], *, failing_case: str | None = None) -> dict:
    return {
        "schema_version": 1,
        "record_type": "phase2e_human_render_decisions",
        "actor": "project-owner",
        "reason": "Listened to every precommitted original/rendered pair.",
        "cases": [
            {
                "id": case_id,
                "join_decisions": [
                    {
                        "join_id": "post-render-join-0001",
                        "decision": "FAIL" if case_id == failing_case else "PASS",
                        "reason": (
                            "Audible defect at the join."
                            if case_id == failing_case
                            else "Join accepted after direct listening comparison."
                        ),
                    }
                ],
            }
            for case_id in case_ids
        ],
    }


def build_bundle(root: Path) -> tuple[Path, list[str]]:
    bundle = root / "bundle"
    case_ids = ["case-1", "case-2", "case-3"]
    sources = ["source-a", "source-b", "source-a"]
    manifest_cases = []
    for index, (case_id, source) in enumerate(zip(case_ids, sources), start=1):
        report_path = write_json(bundle / case_id / "technical_verification.json", technical_report(index))
        manifest_cases.append(
            {
                "id": case_id,
                "audio_source_id": source,
                "technical_report_sha256": FINALIZER.sha256_path(report_path),
            }
        )
    manifest = {
        "schema_version": 1,
        "record_type": "phase2e_human_render_review_bundle",
        "selection_locked_before_listening": True,
        "pre_human_gate": "PASS",
        "closeout_policy": {
            "minimum_rendered_human_cases": 3,
            "minimum_distinct_audio_sources": 2,
            "required_technical_pass_fraction": 1.0,
            "required_human_perceptual_pass_fraction": 1.0,
            "maximum_safety_violations": 0,
            "decision_if_all_pass": "CLOSE_OUT_READY",
            "decision_if_any_fail": "INSUFFICIENT_JOIN_QUALITY",
        },
        "cases": manifest_cases,
    }
    write_json(bundle / "manifest.json", manifest)
    return bundle, case_ids


class Phase2EHumanCloseoutFinalizerTests(unittest.TestCase):
    def test_three_explicit_human_passes_finalize_closeout_ready(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, case_ids = build_bundle(root)
            decisions_path = write_json(root / "decisions.json", decisions(case_ids))
            result = FINALIZER.finalize(bundle, decisions_path, root / "out")
            self.assertEqual(result["status"], "CLOSE_OUT_READY")
            self.assertTrue(result["phase2e_closeout_ready"])
            self.assertFalse(result["auto_apply"])
            for case_id in case_ids:
                self.assertTrue((root / "out" / case_id / "human_render_review.json").is_file())
            self.assertTrue((root / "out" / "phase2e_closeout_decision.json").is_file())

    def test_one_explicit_human_fail_keeps_phase_open(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, case_ids = build_bundle(root)
            decisions_path = write_json(root / "decisions.json", decisions(case_ids, failing_case="case-2"))
            result = FINALIZER.finalize(bundle, decisions_path, root / "out")
            self.assertEqual(result["status"], "INSUFFICIENT_JOIN_QUALITY")
            self.assertFalse(result["phase2e_closeout_ready"])

    def test_missing_or_extra_case_decision_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, case_ids = build_bundle(root)
            payload = decisions(case_ids[:-1])
            decisions_path = write_json(root / "decisions.json", payload)
            with self.assertRaisesRegex(ValueError, "corpus bloqueado"):
                FINALIZER.finalize(bundle, decisions_path, root / "out")

    def test_changed_technical_report_sha_fails_closed_before_review(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, case_ids = build_bundle(root)
            report_path = bundle / "case-1" / "technical_verification.json"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["output"]["sha256"] = "f" * 64
            write_json(report_path, report)
            decisions_path = write_json(root / "decisions.json", decisions(case_ids))
            with self.assertRaisesRegex(ValueError, "technical report SHA"):
                FINALIZER.finalize(bundle, decisions_path, root / "out")

    def test_unknown_join_id_is_rejected_by_human_review_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundle, case_ids = build_bundle(root)
            payload = decisions(case_ids)
            payload["cases"][0]["join_decisions"][0]["join_id"] = "post-render-join-9999"
            decisions_path = write_json(root / "decisions.json", payload)
            with self.assertRaisesRegex(ValueError, "desconocido"):
                FINALIZER.finalize(bundle, decisions_path, root / "out")


if __name__ == "__main__":
    unittest.main()
