import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None
from mt_agent.ffx import run_ffmpeg

APP = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"


@unittest.skipIf(AppTest is None, "streamlit absent")
class Pick(unittest.TestCase):
    def test_decouper_la_selection(self) -> None:
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        r = Path(tmp.name); (r / "inbox").mkdir()
        for n in ("a.mp4", "b.mp4"):
            run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=320x240:d=10:r=25", "-pix_fmt", "yuv420p"], r / "inbox" / n)
        with patch("mt_agent.paths.ROOT", r):
            at = AppTest.from_file(str(APP), default_timeout=120).run()
            self.assertEqual(len(at.exception), 0)
            at.checkbox(key="pick:b.mp4").uncheck().run()
            btn = next(b for b in at.button if b.label == "Découper la sélection (1)")
            btn.click().run()
            self.assertEqual(len(at.exception), 0)
            files = list((r / "workspace" / "plans").iterdir())
            self.assertEqual(len(files), 1)
            self.assertIn("a.mp4", files[0].read_text())
            self.assertNotIn("b.mp4", files[0].read_text())
