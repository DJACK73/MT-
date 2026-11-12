from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent import webapi


def _dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg absent")
class Collage(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "inbox").mkdir()
        for name, size in (("a.mp4", "320x240"), ("b.mp4", "160x300")):
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=30:duration=1",
                            "-pix_fmt", "yuv420p", str(self.root / "inbox" / name)], check=True, capture_output=True)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_bout_et_incrust(self) -> None:
        for mode, expected in (("bout", 2.0), ("incrust", 1.0)):
            r = webapi.run_stack(self.root, "a.mp4", "b.mp4", mode)
            self.assertEqual(r["out"], f"collage/a__b-{mode}.mp4")
            f = self.root / "output" / "collage" / f"a__b-{mode}.mp4"
            self.assertTrue(f.is_file())
            self.assertAlmostEqual(_dur(f), expected, delta=0.25)
