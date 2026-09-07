from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "run_phase2e_12s3s_pipeline_gate.py"
SPEC = importlib.util.spec_from_file_location("phase2e_12s3s_pipeline_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Phase2E12s3sPipelineGateHarnessTests(unittest.TestCase):
    def test_candidate_records_link_by_record_id(self):
        records = [
            {"id": "possible_repetition-0001", "kind": "possible_repetition"},
            {"id": "possible_repetition-0002", "kind": "possible_repetition"},
        ]
        linked = MODULE._candidate_record(records, "possible_repetition-0001")
        self.assertIsNotNone(linked)
        self.assertEqual(linked["id"], "possible_repetition-0001")

    def test_downstream_records_still_link_by_candidate_id(self):
        records = [
            {"id": "semantic-decision-0001", "candidate_id": "possible_repetition-0001"},
            {"id": "semantic-decision-0002", "candidate_id": "possible_repetition-0002"},
        ]
        linked = MODULE._linked_record(records, "possible_repetition-0001")
        self.assertIsNotNone(linked)
        self.assertEqual(linked["id"], "semantic-decision-0001")

    def test_duplicate_links_fail_closed(self):
        candidates = [
            {"id": "possible_repetition-0001"},
            {"id": "possible_repetition-0001"},
        ]
        downstream = [
            {"candidate_id": "possible_repetition-0001"},
            {"candidate_id": "possible_repetition-0001"},
        ]
        self.assertIsNone(MODULE._candidate_record(candidates, "possible_repetition-0001"))
        self.assertIsNone(MODULE._linked_record(downstream, "possible_repetition-0001"))


if __name__ == "__main__":
    unittest.main()
