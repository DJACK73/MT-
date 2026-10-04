import subprocess, tempfile, unittest
from pathlib import Path
from mt_agent.approval import PlanError, approve
from mt_agent.export import build_graph, export_plan
from mt_agent.ffx import MediaError, duration, run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

def _size(p: Path) -> tuple[int, int]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    w, h = r.stdout.strip().split(",")
    return int(w), int(h)

def _plan(src: str, **opt) -> Plan:
    return Plan(options=Options(**opt), sources=[Source(id="a", path=src, duration=6.0)],
                scenes=[Scene(source_id="a", start=0.0, end=2.0, selected=True),
                        Scene(source_id="a", start=2.0, end=3.0),
                        Scene(source_id="a", start=3.0, end=5.0, selected=True)])

class Export(unittest.TestCase):
    def test_graph_known_answer(self):
        p = Plan(options=Options(framing="crop_center"), sources=[Source(id="a", path="x.mp4", duration=9.0)],
                 scenes=[Scene(source_id="a", start=1.0, end=3.0, selected=True)])
        paths, fc = build_graph(p)
        self.assertEqual(paths, ["x.mp4"])
        self.assertEqual(fc, "[0:v]trim=start=1.000:end=3.000,setpts=PTS-STARTPTS,"
                             "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                             "setsar=1,fps=25,format=yuv420p[v0];[v0]concat=n=1:v=1:a=0[out]")
        with self.assertRaises(PlanError):
            build_graph(p.model_copy(update={"scenes": [p.scenes[0].model_copy(update={"selected": False})]}))
    def test_render(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); src = d / "s.mp4"
            run_ffmpeg(["-f", "lavfi", "-i", "testsrc=s=320x240:d=6:r=25", "-pix_fmt", "yuv420p"], src)
            for opt, size in (({"framing": "blur_pad", "profile": "vertical"}, (1080, 1920)),
                              ({"framing": "crop_center", "profile": "vertical"}, (1080, 1920)),
                              ({"framing": "blur_pad", "profile": "youtube"}, (1920, 1080))):
                with self.subTest(opt=opt):
                    plan = approve(_plan(str(src), **opt)); out_dir = d / f"o_{opt['framing']}_{opt['profile']}"
                    mp4, js = export_plan(plan, d, out_dir)
                    self.assertEqual(_size(mp4), size)
                    self.assertAlmostEqual(duration(str(mp4)), 4.0, delta=0.2)
                    self.assertTrue(js.name.endswith(".rendered.json"))
                    with self.assertRaises(PlanError): export_plan(plan.model_copy(update={"status": "rendered"}), d, out_dir)
                    with self.assertRaises(MediaError): export_plan(plan, d, out_dir)  # mp4 existe : refus
                    self.assertEqual(sorted(x.suffix for x in out_dir.iterdir()), [".json", ".mp4"])  # aucun .part
    def test_unapproved_renders_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "o"
            with self.assertRaises(PlanError): export_plan(_plan("x.mp4"), Path(t), out)
            self.assertFalse(out.exists())
if __name__ == "__main__": unittest.main()
