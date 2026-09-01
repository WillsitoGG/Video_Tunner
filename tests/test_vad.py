import unittest

from video_tunner.vad import SpeechInterval, non_speech_gaps


class VadGapTests(unittest.TestCase):
    def test_non_speech_gaps_are_complement_of_merged_speech(self):
        speech = [
            SpeechInterval(1.0, 2.0),
            SpeechInterval(1.8, 3.0),
            SpeechInterval(4.0, 5.0),
        ]
        self.assertEqual(
            non_speech_gaps(speech, duration=6.0),
            [(0.0, 1.0), (3.0, 4.0), (5.0, 6.0)],
        )

    def test_short_gaps_can_be_filtered(self):
        speech = [SpeechInterval(0.0, 1.0), SpeechInterval(1.2, 2.0)]
        self.assertEqual(non_speech_gaps(speech, duration=2.0, min_duration=0.3), [])


if __name__ == "__main__":
    unittest.main()
