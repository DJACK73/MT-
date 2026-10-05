import subprocess, tempfile, unittest
from pathlib import Path
from mt_agent.preview import preview_clip

def _dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)

class PreviewTest(unittest.TestCase):
    def test_duree_et_cache(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = root / "src.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=25:duration=4",
                            "-pix_fmt", "yuv420p", str(src)], check=True)
            a = preview_clip(src, 1.0, 2.5, root)
            self.assertAlmostEqual(_dur(a), 1.5, delta=0.1)
            m = a.stat().st_mtime_ns
            self.assertEqual(preview_clip(src, 1.0, 2.5, root), a)
            self.assertEqual(a.stat().st_mtime_ns, m)

    def test_bornes_invalides(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            src = root / "x.mp4"
            src.write_bytes(b"")
            with self.assertRaises(ValueError):
                preview_clip(src, 2.0, 1.0, root)
