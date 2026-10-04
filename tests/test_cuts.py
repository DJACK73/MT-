import tempfile, unittest
from pathlib import Path
from mt_agent.cuts import detect_cuts
from mt_agent.ffx import MediaError, duration, run_ffmpeg

def _color(c: str, d: int) -> list[str]:
    return ["-f", "lavfi", "-i", f"color=c={c}:s=320x240:d={d}:r=25"]

class Cuts(unittest.TestCase):
    def test_known_answers(self):
        with tempfile.TemporaryDirectory() as t:
            v = str(Path(t) / "s.mp4")
            run_ffmpeg([*_color("red", 3), *_color("blue", 3), *_color("green", 4),
                        "-filter_complex", "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], Path(v))
            self.assertAlmostEqual(duration(v), 10.0, delta=0.1)
            cuts = detect_cuts(v)
            self.assertEqual(len(cuts), 2)
            self.assertAlmostEqual(cuts[0], 3.0, delta=0.1)
            self.assertAlmostEqual(cuts[1], 6.0, delta=0.1)
            with self.assertRaises(MediaError): run_ffmpeg(_color("red", 1), Path(v))  # refus d'écraser
            self.assertAlmostEqual(duration(v), 10.0, delta=0.1)  # source intacte
    def test_errors(self):
        with self.assertRaises(MediaError): duration("/nonexistent.mp4")
        with self.assertRaises(MediaError): run_ffmpeg(["-i", "/nonexistent.mp4", "-f", "null", "-"])
        with self.assertRaises(ValueError): detect_cuts("x", 1.5)
if __name__ == "__main__": unittest.main()
