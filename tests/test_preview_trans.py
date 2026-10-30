import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.preview_trans import Seg, _frame_size, preview_trans, trans_key

HAVE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _make(path: Path, color: str, size: str, secs: int = 2) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s={size}:r=25:d={secs}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    return path


def _dur(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True, check=True)
    return float(json.loads(r.stdout)["format"]["duration"])


class KeyTest(unittest.TestCase):
    def test_key_varies_with_every_setting(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "s.mp4"
            f.write_bytes(b"x")
            a, b = Seg(f, 0.0, 3.0), Seg(f, 3.0, 6.0)
            base = trans_key(a, b, "fade", 0.5)
            self.assertEqual(base, trans_key(a, b, "fade", 0.5))
            others = [trans_key(a, b, "hblur", 0.5), trans_key(a, b, "fade", 0.6),
                      trans_key(a, b, "fade", 0.5, speed=2.0), trans_key(a, b, "fade", 0.5, width=240),
                      trans_key(a, b, "fade", 0.5, ctx=0.5),
                      trans_key(Seg(f, 0.0, 3.0, mirror=True), b, "fade", 0.5),
                      trans_key(a, Seg(f, 3.0, 6.0, zoom=1.5), "fade", 0.5),
                      trans_key(a, Seg(f, 3.5, 6.0), "fade", 0.5)]
            self.assertEqual(len({base, *others}), len(others) + 1)

    def test_invalid_args(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root / "s.mp4"
            f.write_bytes(b"x")
            a, b = Seg(f, 0.0, 3.0), Seg(f, 3.0, 6.0)
            with self.assertRaises(ValueError):
                preview_trans(a, b, root, "zoomin", 0.5)
            with self.assertRaises(ValueError):
                preview_trans(a, b, root, "fade", 1.5)
            with self.assertRaises(ValueError):
                preview_trans(a, Seg(f, 3.0, 3.4), root, "fade", 0.5)


@unittest.skipUnless(HAVE, "ffmpeg/ffprobe requis")
class RenderTest(unittest.TestCase):
    def test_duration_cache_and_size(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = Seg(_make(root / "a.mp4", "red", "160x96"), 0.0, 2.0)
            b = Seg(_make(root / "b.mp4", "blue", "160x96"), 0.0, 2.0)
            out = preview_trans(a, b, root, "fade", 0.5, width=128, ctx=0.5)
            self.assertEqual(_frame_size(out), (128, 76))
            self.assertAlmostEqual(_dur(out), 1.5, delta=0.15)
            m = out.stat().st_mtime_ns
            self.assertEqual(preview_trans(a, b, root, "fade", 0.5, width=128, ctx=0.5), out)
            self.assertEqual(out.stat().st_mtime_ns, m)

    def test_other_aspect_same_size(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = Seg(_make(root / "a.mp4", "red", "160x96"), 0.0, 2.0)
            b = Seg(_make(root / "b.mp4", "blue", "96x160"), 0.0, 2.0)
            out = preview_trans(a, b, root, "slideleft", 0.5, width=128, ctx=0.5)
            self.assertEqual(_frame_size(out), (128, 76))
            self.assertAlmostEqual(_dur(out), 1.5, delta=0.15)

    def test_options_render(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            a = Seg(_make(root / "a.mp4", "red", "160x96"), 0.0, 2.0, mirror=True, zoom=1.5)
            b = Seg(_make(root / "b.mp4", "blue", "160x96"), 0.0, 2.0)
            out = preview_trans(a, b, root, "hblur", 0.5, speed=2.0, width=128, ctx=0.5)
            self.assertAlmostEqual(_dur(out), 1.5, delta=0.15)


if __name__ == "__main__":
    unittest.main()
