import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_tunner import tools


class PortableToolResolutionTests(unittest.TestCase):
    def test_strict_mode_never_falls_back_to_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bundled = root / "Tools" / "ffmpeg" / "bin" / tools._tool_filename("ffmpeg")
            bundled.parent.mkdir(parents=True)

            with (
                patch.dict(os.environ, {"VIDEO_TUNNER_PORTABLE_STRICT": "1"}, clear=False),
                patch.object(tools, "runtime_root", return_value=root),
                patch.object(tools.shutil, "which", return_value="/external/ffmpeg"),
            ):
                self.assertEqual(tools.tool_candidates("ffmpeg"), [bundled])

    def test_strict_model_root_is_inside_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with (
                patch.dict(
                    os.environ,
                    {
                        "VIDEO_TUNNER_PORTABLE_STRICT": "1",
                        "VIDEO_TUNNER_MODEL_DIR": str(root / "external-models"),
                    },
                    clear=False,
                ),
                patch.object(tools, "runtime_root", return_value=root),
            ):
                self.assertEqual(tools.model_root(), root / "Models")

    def test_runtime_layout_can_be_created_under_runtime_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with patch.object(tools, "runtime_root", return_value=root):
                layout = tools.ensure_runtime_layout()
                for key in ("models", "temp", "cache", "config", "logs", "output"):
                    self.assertTrue(layout[key].is_dir())


if __name__ == "__main__":
    unittest.main()
