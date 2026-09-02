from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner.transcription import (
    _model_directory_name,
    local_whisper_model_path,
    whisper_model_status,
)


class WhisperModelResolutionTests(unittest.TestCase):
    def test_model_directory_name_is_portable(self) -> None:
        self.assertEqual(_model_directory_name("org/model:name"), "org__model_name")

    def test_status_requires_offline_safe_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("video_tunner.transcription.model_root", return_value=root):
                model = local_whisper_model_path("tiny")
                model.mkdir(parents=True)
                (model / "config.json").write_text("{}", encoding="utf-8")
                (model / "model.bin").write_bytes(b"model")
                self.assertFalse(whisper_model_status("tiny")["available"])
                (model / "tokenizer.json").write_text("{}", encoding="utf-8")
                self.assertTrue(whisper_model_status("tiny")["available"])

    def test_model_path_stays_under_whisper_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch("video_tunner.transcription.model_root", return_value=root):
                expected = root / "whisper" / "large-v3-turbo"
                self.assertEqual(local_whisper_model_path("large-v3-turbo"), expected)


if __name__ == "__main__":
    unittest.main()
