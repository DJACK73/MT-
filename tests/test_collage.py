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
            r = webapi.run_stack(self.root, ["a.mp4", "b.mp4"], mode)
            self.assertEqual(r["out"], f"collage/a__b-{mode}.mp4")
            f = self.root / "output" / "collage" / f"a__b-{mode}.mp4"
            self.assertTrue(f.is_file())
            self.assertAlmostEqual(_dur(f), expected, delta=0.25)

    @staticmethod
    def _dims(p: Path) -> tuple[int, int]:
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                            "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
        w, h = r.stdout.strip().split(",")[:2]
        return int(w), int(h)

    def test_trois_bout(self) -> None:
        r = webapi.run_stack(self.root, ["a.mp4", "b.mp4", "a.mp4"], "bout")
        self.assertEqual(r["out"], "collage/a__b__a-bout.mp4")
        self.assertAlmostEqual(_dur(self.root / "output" / r["out"]), 3.0, delta=0.4)

    def test_grille_trois_et_quatre(self) -> None:
        for names, tag in ((["a.mp4", "b.mp4", "a.mp4"], "a__b__a"), (["a.mp4", "b.mp4", "a.mp4", "b.mp4"], "a__b__a__b")):
            r = webapi.run_stack(self.root, names, "grille")
            self.assertEqual(r["out"], f"collage/{tag}-grille.mp4")
            f = self.root / "output" / r["out"]
            self.assertEqual(self._dims(f), (720, 1280))
            self.assertAlmostEqual(_dur(f), 1.0, delta=0.25)

    def test_remplir(self) -> None:
        r = webapi.run_stack(self.root, ["a.mp4", "b.mp4"], "bout", "remplir")
        self.assertEqual(r["out"], "collage/a__b-bout-remplir.mp4")
        self.assertEqual(self._dims(self.root / "output" / r["out"]), (720, 1280))

    def test_limites(self) -> None:
        a = "a.mp4"
        for names, mode, fit in (([a] * 4, "cote", "ajuster"), ([a, a], "grille", "ajuster"), ([a] * 3, "incrust", "ajuster"),
                                 ([a], "bout", "ajuster"), ([a] * 5, "bout", "ajuster"), ([a, a], "bout", "zzz"),
                                 ("a.mp4", "bout", "ajuster")):
            with self.assertRaises(ValueError):
                webapi.run_stack(self.root, names, mode, fit)
