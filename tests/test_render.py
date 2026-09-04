import unittest

from video_tunner.render import keep_segments, render_from_plan


class RenderPlanTests(unittest.TestCase):
    def test_keep_segments_merges_overlapping_cuts(self):
        edits = [
            {"action": "remove", "start": 1.0, "end": 2.0},
            {"action": "remove", "start": 1.5, "end": 3.0},
            {"action": "remove", "start": 8.0, "end": 9.0},
        ]
        self.assertEqual(keep_segments(10.0, edits), [(0.0, 1.0), (3.0, 8.0), (9.0, 10.0)])

    def test_invalid_or_non_remove_edits_do_not_break_plan(self):
        edits = [
            {"action": "review", "start": 1.0, "end": 2.0},
            {"action": "remove", "start": 4.0, "end": 4.0},
        ]
        self.assertEqual(keep_segments(5.0, edits), [(0.0, 5.0)])

    def test_renderer_rejects_non_executable_plan_proposal(self):
        proposal = {
            "schema_version": 1,
            "artifact_type": "approved_edit_plan_proposal",
            "source": {"duration_seconds": 10.0},
            "proposed_edits": [
                {"action": "remove", "start": 1.0, "end": 2.0, "executable": False}
            ],
            "render_authorization": False,
            "executable": False,
        }
        with self.assertRaisesRegex(ValueError, "Proposal no es ejecutable"):
            render_from_plan("input.mp4", proposal, "output.mp4")


if __name__ == "__main__":
    unittest.main()
