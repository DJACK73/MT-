import tempfile, unittest
from pathlib import Path
from mt_agent.export import Look, _look, _node
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source


def _plan(**opt) -> Plan:
    return Plan(options=Options(**opt), sources=[Source(id="a", path="x.mp4", duration=9.0)],
                scenes=[Scene(source_id="a", start=0, end=4)])


class LookTests(unittest.TestCase):
    def test_defauts_inchanges(self) -> None:
        n = _node(0, 0, 0.0, 3.0, "crop_center", 1080, 1920)
        self.assertIn("crop=1080:1920,setsar", n)
        self.assertNotIn("(iw-ow)", n)
        self.assertIn("boxblur", _node(0, 0, 0.0, 3.0, "blur_pad", 1080, 1920))

    def test_position_et_noir(self) -> None:
        self.assertIn("crop=1080:1920:(iw-ow)*0.000:(ih-oh)/2",
                      _node(0, 0, 0.0, 3.0, "crop_center", 1080, 1920, "blur", 0.0))
        n = _node(0, 0, 0.0, 3.0, "blur_pad", 1080, 1920, "black")
        self.assertIn("pad=1080:1920", n)
        self.assertNotIn("boxblur", n)

    def test_resolution(self) -> None:
        self.assertEqual(_look(_plan(), None), ("blur_pad", "blur", 0.5))
        self.assertEqual(_look(_plan(framing="crop_center"), None)[0], "crop_center")
        self.assertEqual(_look(_plan(framing="crop_center"), Look(fit="bars"))[0], "blur_pad")
        self.assertEqual(_look(_plan(), Look(fit="fill", anchor=1.0)), ("crop_center", "blur", 1.0))
        with self.assertRaises(Exception):
            _look(_plan(), Look(fit="fill", anchor=1.5))

    def test_rendu_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); src = d / "s.mp4"
            run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=320x240:d=3:r=25", "-pix_fmt", "yuv420p"], src)
            for k, (fr, bg, cx) in enumerate([("blur_pad", "blur", 0.5), ("blur_pad", "black", 0.5),
                                              ("crop_center", "blur", 0.0), ("crop_center", "blur", 1.0)]):
                out = d / f"o{k}.mp4"
                run_ffmpeg(["-i", str(src), "-filter_complex", _node(0, 0, 0.0, 3.0, fr, 1080, 1920, bg, cx),
                            "-map", "[v0]", "-c:v", "libx264", "-preset", "veryfast"], out)
                self.assertGreater(out.stat().st_size, 0)
