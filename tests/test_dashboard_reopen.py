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


def _btn(at, label: str):
    return next(b for b in at.button if b.label == label)


def _metric(at, label: str) -> str:
    return next(m.value for m in at.metric if m.label == label)


@unittest.skipIf(AppTest is None, "streamlit absent")
class Reopen(unittest.TestCase):
    def test_appliquer_vers_plan_existant(self) -> None:
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        r = Path(tmp.name); (r / "inbox").mkdir()
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=320x240:d=10:r=25", "-pix_fmt", "yuv420p"], r / "inbox" / "s.mp4")
        plan = Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=10.0)],
                    scenes=[Scene(source_id="a", start=0, end=3, selected=True),
                            Scene(source_id="a", start=3, end=6, selected=True),
                            Scene(source_id="a", start=6, end=10, selected=True)])
        d = r / "workspace" / "plans"; d.mkdir(parents=True)
        orig = save_plan(plan, d)
        with patch("mt_agent.paths.ROOT", r):
            at = AppTest.from_file(str(APP), default_timeout=60).run()
            self.assertEqual(_metric(at, "Scènes"), "3/3")
            at.text_input(key="spec").set_value("1-2").run()
            _btn(at, "Appliquer la sélection").click().run()
            self.assertEqual(_metric(at, "Scènes"), "2/3")
            _btn(at, "Approuver").click().run()
            self.assertEqual(_metric(at, "Statut"), "Approuvé")
            _btn(at, "Tout cocher").click().run()
            _btn(at, "Appliquer la sélection").click().run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(len(at.error), 0)
            self.assertEqual(at.session_state["plan_path"], str(orig))
            self.assertEqual(_metric(at, "Scènes"), "3/3")
