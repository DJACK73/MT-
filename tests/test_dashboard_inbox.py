import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None
from mt_agent.approval import save_plan
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Plan, Scene, Source

APP = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"


@unittest.skipIf(AppTest is None, "streamlit absent")
class InboxMarks(unittest.TestCase):
    def test_marque_decoupee_ou_non(self) -> None:
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        r = Path(tmp.name); (r / "inbox").mkdir()
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=320x240:d=10:r=25", "-pix_fmt", "yuv420p"], r / "inbox" / "a.mp4")
        (r / "inbox" / "b.mp4").write_bytes(b"")
        plan = Plan(sources=[Source(id="a", path="inbox/a.mp4", duration=10.0)],
                    scenes=[Scene(source_id="a", start=0, end=5, selected=True),
                            Scene(source_id="a", start=5, end=10, selected=True)])
        d = r / "workspace" / "plans"; d.mkdir(parents=True)
        save_plan(plan, d)
        with patch("mt_agent.paths.ROOT", r):
            at = AppTest.from_file(str(APP), default_timeout=60).run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(list(at.selectbox(key="scan_video").options), ["✓ a.mp4", "○ b.mp4"])
