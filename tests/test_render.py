import unittest

from video_tunner.render import keep_segments


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


if __name__ == "__main__":
    unittest.main()
