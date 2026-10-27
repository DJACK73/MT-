import subprocess, tempfile, unittest
from pathlib import Path
from mt_agent.ffx import run_ffmpeg
from mt_agent.preview import preview_clip, preview_key


class PreviewZoom(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.r = Path(t.name); (self.r / "inbox").mkdir()
        self.src = self.r / "inbox" / "bwb.mp4"  # noir 32 | blanc 64 | noir 32
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=black:s=32x64:d=2:r=25",
                    "-f", "lavfi", "-i", "color=c=white:s=64x64:d=2:r=25",
                    "-f", "lavfi", "-i", "color=c=black:s=32x64:d=2:r=25",
                    "-filter_complex", "[0][1][2]hstack=inputs=3", "-pix_fmt", "yuv420p"], self.src)

    def _left(self, clip: Path) -> int:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-frames:v", "1", "-vf",
                              "scale=2:1:flags=area,format=gray", "-f", "rawvideo", "-"],
                             check=True, capture_output=True).stdout
        return raw[0]

    def test_cle_inchangee_sans_zoom(self) -> None:
        self.assertEqual(preview_key(self.src, 0, 1, 128), preview_key(self.src, 0, 1, 128, False, 1.0))

    def test_cle_distincte_avec_zoom(self) -> None:
        self.assertNotEqual(preview_key(self.src, 0, 1, 128), preview_key(self.src, 0, 1, 128, False, 1.5))

    def test_zoom_recadre_au_centre(self) -> None:
        self.assertLess(self._left(preview_clip(self.src, 0, 1, self.r, 128)), 200)
        self.assertGreater(self._left(preview_clip(self.src, 0, 1, self.r, 128, zoom=2.0)), 200)

    def test_zoom_hors_bornes(self) -> None:
        for z in (0.9, 2.1):
            with self.assertRaises(ValueError):
                preview_clip(self.src, 0, 1, self.r, 128, zoom=z)


if __name__ == "__main__":
    unittest.main()
