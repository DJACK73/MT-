import tempfile, unittest
from pathlib import Path
from mt_agent.approval import approve
from mt_agent.compose import compose_plan
from mt_agent.export import export_clips, export_plan
from mt_agent.ffx import duration, run_ffmpeg
from mt_agent.models import Plan, Scene, Source


class ComposeExport(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.r = Path(t.name); (self.r / "inbox").mkdir()
        for name, col in (("a.mp4", "red"), ("b.mp4", "blue")):
            run_ffmpeg(["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d=4:r=25", "-pix_fmt", "yuv420p"],
                       self.r / "inbox" / name)
        pa = Plan(sources=[Source(id="a", path="inbox/a.mp4", duration=4.0)],
                  scenes=[Scene(source_id="a", start=0, end=1), Scene(source_id="a", start=1, end=2)])
        pb = Plan(sources=[Source(id="a", path="inbox/b.mp4", duration=4.0)],
                  scenes=[Scene(source_id="a", start=0, end=1.5)])
        self.plan = approve(compose_plan([pa, pb], [(1, 1), (0, 2), (0, 1)]))

    def test_clips_nommes_par_rang_et_video(self) -> None:
        files = export_clips(self.plan, self.r, self.r / "output")
        self.assertEqual([f.name for f in files], ["001-B.mp4", "002-A.mp4", "003-A.mp4"])
        self.assertTrue(files[0].parent.name.startswith("montage-"))

    def test_assemble_suit_l_ordre(self) -> None:
        mp4, _ = export_plan(self.plan, self.r, self.r / "output")
        self.assertAlmostEqual(duration(str(mp4)), 3.5, delta=0.3)
