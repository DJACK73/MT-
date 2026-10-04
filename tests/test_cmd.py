import contextlib, io, tempfile, unittest
from pathlib import Path
from mt_agent.cmd import main
from mt_agent.ffx import duration, run_ffmpeg
from mt_agent.models import Plan

def _run(argv: list[str], root: Path) -> tuple[int, str]:
    buf, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(err):
        return main(argv, root), buf.getvalue().strip()

class Cmd(unittest.TestCase):
    def test_full_flow(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t); (r / "inbox").mkdir(); v = r / "inbox" / "s.mp4"
            c = lambda col, d: ["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d={d}:r=25"]
            run_ffmpeg([*c("red", 3), *c("blue", 3), *c("green", 4), "-filter_complex",
                        "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], v)
            code, pending = _run(["scan", str(v)], r)
            self.assertEqual(code, 0); self.assertTrue(pending.endswith(".pending_human_review.json"))
            plan = Plan.model_validate_json(Path(pending).read_text())
            self.assertEqual([(round(s.start, 1), round(s.end, 1)) for s in plan.scenes], [(0.0, 3.0), (3.0, 6.0), (6.0, 10.0)])
            self.assertEqual(plan.sources[0].path, "inbox/s.mp4")
            code, _ = _run(["export", pending], r)                       # non approuvé : refus
            self.assertEqual(code, 1); self.assertFalse((r / "output").exists())
            code, approved = _run(["approve", pending], r); self.assertEqual(code, 0)
            self.assertEqual(_run(["approve", pending], r)[0], 1)         # 2e approbation : refus d'écraser
            code, out = _run(["export", approved], r.resolve()); self.assertEqual(code, 0)
            self.assertAlmostEqual(duration(out.splitlines()[0]), 10.0, delta=0.2)
            self.assertEqual(_run(["export", approved], r)[0], 1)         # pas d'écrasement
            self.assertEqual([p.name for p in (r / "inbox").iterdir()], ["s.mp4"])
    def test_errors(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(_run(["scan", "/nonexistent.mp4"], Path(t))[0], 1)
            self.assertEqual(_run(["export", "/nonexistent.json"], Path(t))[0], 1)
if __name__ == "__main__": unittest.main()
