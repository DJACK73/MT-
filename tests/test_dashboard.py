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
class Dashboard(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.r = Path(t.name); (self.r / "inbox").mkdir()
        c = lambda col, d: ["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d={d}:r=25"]
        run_ffmpeg([*c("red", 3), *c("blue", 3), *c("green", 4), "-filter_complex",
                    "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], self.r / "inbox" / "s.mp4")
        plan = Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=10.0)],
                    scenes=[Scene(source_id="a", start=0, end=3), Scene(source_id="a", start=3, end=6),
                            Scene(source_id="a", start=6, end=10)])
        d = self.r / "workspace" / "plans"; d.mkdir(parents=True)
        save_plan(plan, d)
        self.out = self.r / "output"
        self.enterContext(patch("mt_agent.paths.ROOT", self.r))

    def test_flow(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(_metric(at, "Statut"), "pending_human_review")
        self.assertEqual(_metric(at, "Scènes"), "0/3")
        self.assertTrue(_btn(at, "Exporter").disabled)
        self.assertFalse(_btn(at, "Approuver").disabled)
        at.text_input(key="spec").set_value("1-2").run()
        _btn(at, "Appliquer la sélection").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(_metric(at, "Scènes"), "2/3")
        _btn(at, "Approuver").click().run()
        self.assertEqual(_metric(at, "Statut"), "approved")
        self.assertFalse(_btn(at, "Exporter").disabled)
        self.assertEqual(list(self.out.glob("*.mp4")), [])      # approuver n'exporte jamais
        _btn(at, "Exporter").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(self.out.glob("*.mp4"))), 1)

    def test_cases(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertEqual(len(at.checkbox), 3)
        at.checkbox[0].check().run()
        at.checkbox[2].check().run()
        _btn(at, "Appliquer la sélection").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(_metric(at, "Scènes"), "2/3")
        self.assertEqual([c.value for c in at.checkbox], [True, False, True])
        _btn(at, "Tout cocher").click().run()
        self.assertEqual([c.value for c in at.checkbox], [True, True, True])
        _btn(at, "Tout décocher").click().run()
        self.assertEqual([c.value for c in at.checkbox], [False, False, False])

    def test_decouper(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self.assertEqual(len(at.exception), 0)
        _btn(at, "Découper").click().run()
        self.assertEqual(len(at.exception), 0)
        maxes = [Plan.model_validate_json(f.read_text()).options.max_scene_seconds
                 for f in (self.r / "workspace" / "plans").iterdir()]
        self.assertIn(5.0, maxes)
