import unittest

from video_tunner.silence import SilenceInterval, parse_silencedetect, silence_removals


class SilenceTests(unittest.TestCase):
    def test_parse_complete_and_trailing_silence(self):
        stderr = """
[silencedetect @ x] silence_start: 1.2
[silencedetect @ x] silence_end: 2.4 | silence_duration: 1.2
[silencedetect @ x] silence_start: 8.0
"""
        self.assertEqual(
            parse_silencedetect(stderr, media_duration=10.0),
            [SilenceInterval(1.2, 2.4), SilenceInterval(8.0, 10.0)],
        )

    def test_silence_removal_preserves_pause(self):
        cuts = silence_removals([SilenceInterval(1.0, 2.0)], keep_pause=0.2)
        self.assertEqual(cuts[0]["start"], 1.1)
        self.assertEqual(cuts[0]["end"], 1.9)
        self.assertAlmostEqual(cuts[0]["duration"], 0.8)


if __name__ == "__main__":
    unittest.main()
