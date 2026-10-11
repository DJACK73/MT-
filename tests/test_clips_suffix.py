import tempfile, unittest
from pathlib import Path

from mt_agent.approval import approve
from mt_agent.export import Look, export_clips
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Plan, Scene, Source


class ClipsSuffix(unittest.TestCase):
    def test_deux_exports(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "inbox").mkdir()
            run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=320x240:d=2:r=25", "-pix_fmt", "yuv420p"],
                       root / "inbox" / "s.mp4")
            plan = approve(Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=2.0)],
                                scenes=[Scene(source_id="a", start=0, end=2, selected=True)]))
            a = export_clips(plan, root, root / "output", look=Look(fit="none"))
            b = export_clips(plan, root, root / "output", look=Look(fit="none"))
            self.assertEqual(b[0].parent.name, a[0].parent.name + "-2")
            self.assertTrue(a[0].is_file() and b[0].is_file())


if __name__ == "__main__":
    unittest.main()
