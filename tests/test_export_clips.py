import tempfile
import unittest
from pathlib import Path

from mt_agent.approval import PlanError, approve
from mt_agent.export import export_clips
from mt_agent.ffx import duration, run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

SPANS = [(0.0, 1.5), (1.5, 3.0), (3.0, 4.5), (4.5, 6.0)]
KEEP = [True, False, True, True]


def _plan(root: Path) -> Plan:
    src = root / "inbox" / "src.mp4"
    src.parent.mkdir(parents=True)
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=320x240:rate=25", "-t", "6",
                "-c:v", "libx264", "-pix_fmt", "yuv420p"], src)
    return Plan(options=Options(framing="crop_center"),
                sources=[Source(id="s", path="inbox/src.mp4", duration=6.0)],
                scenes=[Scene(source_id="s", start=a, end=b, selected=k)
                        for (a, b), k in zip(SPANS, KEEP)])


class ExportClipsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plan = approve(_plan(self.root))
        self.out = self.root / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_un_fichier_par_scene_dans_l_ordre(self) -> None:
        calls: list[tuple[int, int]] = []
        files = export_clips(self.plan, self.root, self.out, on_progress=lambda k, n: calls.append((k, n)))
        self.assertEqual([f.name for f in files], ["001.mp4", "003.mp4", "004.mp4"])
        self.assertEqual(sorted(x.name for x in files[0].parent.iterdir()), ["001.mp4", "003.mp4", "004.mp4"])
        self.assertEqual(files[0].parent.parent, self.out / "clips")
        self.assertTrue(files[0].parent.name.startswith("src-"))
        self.assertEqual(calls, [(1, 3), (2, 3), (3, 3)])
        for f in files:
            self.assertAlmostEqual(duration(str(f)), 1.5, delta=0.15)

    def test_refus_ecraser(self) -> None:
        export_clips(self.plan, self.root, self.out)
        with self.assertRaises(PlanError):
            export_clips(self.plan, self.root, self.out)

    def test_refus_non_approuve(self) -> None:
        pending = self.plan.model_copy(update={"status": "pending_human_review"})
        with self.assertRaises(PlanError):
            export_clips(pending, self.root, self.out)

    def test_refus_inbox(self) -> None:
        with self.assertRaises(PermissionError):
            export_clips(self.plan, self.root, self.root / "inbox" / "o")

    def test_aucune_scene(self) -> None:
        none = self.plan.model_copy(update={
            "scenes": [s.model_copy(update={"selected": False}) for s in self.plan.scenes],
            "status": "pending_human_review", "approved_hash": None})
        with self.assertRaises(PlanError):
            export_clips(approve(none), self.root, self.out)


if __name__ == "__main__":
    unittest.main()
