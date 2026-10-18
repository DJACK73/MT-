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
class DashboardCompose(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.r = Path(t.name); (self.r / "inbox").mkdir()
        c = lambda col, d: ["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d={d}:r=25"]
        run_ffmpeg([*c("red", 3), *c("blue", 3), *c("green", 4), "-filter_complex",
                    "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], self.r / "inbox" / "s.mp4")
        (self.r / "inbox" / "t.mp4").write_bytes((self.r / "inbox" / "s.mp4").read_bytes())
        self.plans = self.r / "workspace" / "plans"; self.plans.mkdir(parents=True)
        pa = Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=10.0)],
                  scenes=[Scene(source_id="a", start=0, end=3), Scene(source_id="a", start=3, end=6),
                          Scene(source_id="a", start=6, end=10)])
        pb = Plan(sources=[Source(id="a", path="inbox/t.mp4", duration=10.0)],
                  scenes=[Scene(source_id="a", start=0, end=3), Scene(source_id="a", start=3, end=6)])
        self.pa, self.pb = str(save_plan(pa, self.plans)), str(save_plan(pb, self.plans))
        self.enterContext(patch("mt_agent.paths.ROOT", self.r))

    def _open(self):
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.exception), 0)
        return at

    def _ck(self, at, p: str, n: int):
        return at.checkbox(key=f"cmp:{Path(p).name}:{n}")

    def _tick(self, at) -> None:
        self._ck(at, self.pb, 2).check().run()
        self._ck(at, self.pa, 1).check().run()
        self._ck(at, self.pa, 3).check().run()

    def test_ordre_de_cochage_puis_clips(self) -> None:
        at = self._open()
        self._tick(at)
        self.assertEqual(at.session_state["cmp_order"], [(self.pb, 2), (self.pa, 1), (self.pa, 3)])
        _btn(at, "Composer le montage").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        new = next(x for x in (Plan.model_validate_json(f.read_text()) for f in self.plans.iterdir())
                   if len(x.sources) == 2)
        self.assertEqual([x.path for x in new.sources], ["inbox/s.mp4", "inbox/t.mp4"])
        self.assertEqual([(c.source_id, c.start, c.end) for c in new.scenes],
                         [("s1", 3.0, 6.0), ("s0", 0.0, 3.0), ("s0", 6.0, 10.0)])
        self.assertEqual(_metric(at, "Scènes"), "3/3")
        _btn(at, "Approuver").click().run()
        _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        names = sorted(f.name for f in (self.r / "output").glob("clips/*/*.mp4"))
        self.assertEqual(names, ["001-B.mp4", "002-A.mp4", "003-A.mp4"])

    def test_monter_retirer(self) -> None:
        at = self._open()
        self._tick(at)
        at.button(key="cmp_dn_0").click().run()
        self.assertEqual(at.session_state["cmp_order"], [(self.pa, 1), (self.pb, 2), (self.pa, 3)])
        at.button(key="cmp_rm_1").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["cmp_order"], [(self.pa, 1), (self.pa, 3)])
        self.assertFalse(self._ck(at, self.pb, 2).value)

    def test_decocher_un_plan(self) -> None:
        at = self._open()
        self.assertEqual(at.session_state["cmp_plans"], [self.pa, self.pb])
        at.checkbox(key=f"cmpp:{Path(self.pb).name}").uncheck().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.session_state["cmp_plans"], [self.pa])
