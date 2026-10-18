import tempfile, unittest
from pathlib import Path
from mt_agent.ffx import run_ffmpeg

class PartUnique(unittest.TestCase):
    def test_part_d_un_autre_appel_intact(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "o.mp4"
            autre = Path(d) / "o.mp4.part"
            autre.write_bytes(b"x")
            run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=64x64:d=1:r=25", "-pix_fmt", "yuv420p"], out)
            self.assertTrue(out.is_file())
            self.assertEqual(autre.read_bytes(), b"x")
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["o.mp4", "o.mp4.part"])

if __name__ == "__main__":
    unittest.main()
