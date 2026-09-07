import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "build_phase2e_review_bundle_case.py"
SPEC = importlib.util.spec_from_file_location("phase2e_review_bundle_case", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class Phase2EReviewBundleToolingTests(unittest.TestCase):
    def test_host_verifier_clears_inherited_strict_mode_and_binds_exact_portable_dir(self):
        with tempfile.TemporaryDirectory() as temp:
            tool_dir = Path(temp)
            suffix = ".exe" if os.name == "nt" else ""
            (tool_dir / f"ffmpeg{suffix}").write_bytes(b"stub")
            (tool_dir / f"ffprobe{suffix}").write_bytes(b"stub")

            with patch.dict(
                os.environ,
                {
                    "VIDEO_TUNNER_PORTABLE_STRICT": "1",
                    "VIDEO_TUNNER_FFMPEG_DIR": str(tool_dir / "wrong"),
                },
                clear=False,
            ):
                resolved = MODULE.configure_host_verifier_tools(tool_dir)
                self.assertEqual(resolved, tool_dir.resolve())
                self.assertNotIn("VIDEO_TUNNER_PORTABLE_STRICT", os.environ)
                self.assertEqual(os.environ["VIDEO_TUNNER_FFMPEG_DIR"], str(tool_dir.resolve()))

    def test_host_verifier_fails_closed_if_exact_portable_tools_are_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            tool_dir = Path(temp)
            suffix = ".exe" if os.name == "nt" else ""
            (tool_dir / f"ffmpeg{suffix}").write_bytes(b"stub")

            with self.assertRaisesRegex(FileNotFoundError, "ffprobe"):
                MODULE.configure_host_verifier_tools(tool_dir)


if __name__ == "__main__":
    unittest.main()
