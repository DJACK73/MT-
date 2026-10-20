import subprocess, tempfile, unittest
from pathlib import Path
from mt_agent.ffx import run_ffmpeg
from mt_agent.preview import preview_clip, preview_key


class PreviewMirror(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.r = Path(t.name); (self.r / "inbox").mkdir()
        self.src = self.r / "inbox" / "lr.mp4"
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=white:s=64x64:d=2:r=25", "-f", "lavfi",
                    "-i", "color=c=black:s=64x64:d=2:r=25", "-filter_complex", "[0][1]hstack",
                    "-pix_fmt", "yuv420p"], self.src)

    def _lr(self, clip: Path) -> tuple[int, int]:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-frames:v", "1", "-vf",
                              "scale=2:1:flags=area,format=gray", "-f", "rawvideo", "-"],
                             check=True, capture_output=True).stdout
        return raw[0], raw[1]

    def test_normal_blanc_a_gauche(self) -> None:
        left, right = self._lr(preview_clip(self.src, 0, 1, self.r, 128))
        self.assertGreater(left, 150)
        self.assertLess(right, 100)

    def test_miroir_noir_a_gauche_et_cle_distincte(self) -> None:
        a = preview_clip(self.src, 0, 1, self.r, 128)
        b = preview_clip(self.src, 0, 1, self.r, 128, mirror=True)
        self.assertNotEqual(a, b)
        self.assertNotEqual(preview_key(self.src, 0, 1, 128), preview_key(self.src, 0, 1, 128, True))
        left, right = self._lr(b)
        self.assertLess(left, 100)
        self.assertGreater(right, 150)
