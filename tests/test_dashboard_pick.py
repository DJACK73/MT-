import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None
from importlib import import_module
from mt_agent.approval import save_plan
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

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
            at.checkbox(key="pick:a.mp4").check().run()
            btn = next(b for b in at.button if b.label == "Découper la sélection (1)")
            btn.click().run()
            self.assertEqual(len(at.exception), 0)
            files = list((r / "workspace" / "plans").iterdir())
            self.assertEqual(len(files), 1)
            self.assertIn("a.mp4", files[0].read_text())
            self.assertNotIn("b.mp4", files[0].read_text())

    def _racine_avec_plan(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        r = Path(tmp.name); (r / "inbox").mkdir()
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=red:s=320x240:d=10:r=25", "-pix_fmt", "yuv420p"], r / "inbox" / "a.mp4")
        (r / "inbox" / "b.mp4").write_bytes(b"")
        plan = Plan(options=Options(min_scene_seconds=3.0, max_scene_seconds=5.0),
                    sources=[Source(id="a", path="inbox/a.mp4", duration=10.0)],
                    scenes=[Scene(source_id="a", start=0, end=5, selected=True),
                            Scene(source_id="a", start=5, end=10, selected=True)])
        d = r / "workspace" / "plans"; d.mkdir(parents=True)
        return r, d, save_plan(plan, d)

    def test_aucune_case_cochee_au_depart(self) -> None:
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        r = Path(tmp.name); (r / "inbox").mkdir()
        for n in ("a.mp4", "b.mp4"):
            (r / "inbox" / n).write_bytes(b"")
        with patch("mt_agent.paths.ROOT", r):
            at = AppTest.from_file(str(APP), default_timeout=60).run()
            self.assertEqual(len(at.exception), 0)
            boxes = [c for c in at.checkbox if str(c.key).startswith("pick:")]
            self.assertEqual(len(boxes), 2)
            self.assertFalse(any(c.value for c in boxes))
            self.assertTrue(at.button(key="b_scan_many").disabled)

    def test_video_deja_coupee_rouverte_sans_scan(self) -> None:
        r, d, saved = self._racine_avec_plan()
        real = import_module("mt_agent.cmd").scan_video
        with patch("mt_agent.paths.ROOT", r), patch("mt_agent.cmd.scan_video", wraps=real) as scan:
            at = AppTest.from_file(str(APP), default_timeout=120).run()
            self.assertEqual(len(at.exception), 0)
            at.checkbox(key="pick:a.mp4").check().run()
            next(b for b in at.button if b.label == "Découper la sélection (1)").click().run()
            self.assertEqual(len(at.exception), 0)
            scan.assert_not_called()
            self.assertEqual(len(list(d.iterdir())), 1)
            self.assertEqual([Path(x).name for x in at.session_state["last_cut"]], [saved.name])

    def test_options_changees_nouveau_plan(self) -> None:
        r, d, saved = self._racine_avec_plan()
        real = import_module("mt_agent.cmd").scan_video
        with patch("mt_agent.paths.ROOT", r), patch("mt_agent.cmd.scan_video", wraps=real) as scan:
            at = AppTest.from_file(str(APP), default_timeout=120).run()
            at.number_input(key="scan_lo").set_value(2.0).run()
            at.checkbox(key="pick:a.mp4").check().run()
            next(b for b in at.button if b.label == "Découper la sélection (1)").click().run()
            self.assertEqual(len(at.exception), 0)
            scan.assert_called_once()
