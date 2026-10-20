import subprocess, tempfile, unittest
from unittest import mock
from pathlib import Path
from mt_agent.approval import PlanError
from mt_agent.ffx import MediaError, run_ffmpeg
from mt_agent.models import Plan, Scene, Source
from mt_agent.thumbs import make_thumbnails, thumbs_key

def _rgb(p: Path) -> tuple[int, int, int]:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-vf", "scale=1:1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       capture_output=True, check=True)
    return tuple(r.stdout[:3])

class Thumbs(unittest.TestCase):
    def test_known_colors(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t); (r / "inbox").mkdir(); v = r / "inbox" / "s.mp4"
            c = lambda col, d: ["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d={d}:r=25"]
            run_ffmpeg([*c("red", 3), *c("blue", 3), *c("green", 4), "-filter_complex",
                        "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], v)
            plan = Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=10.0)],
                        scenes=[Scene(source_id="a", start=0, end=3), Scene(source_id="a", start=3, end=6),
                                Scene(source_id="a", start=6, end=10)])
            th = make_thumbnails(plan, r)
            self.assertEqual(len(th), 3)
            (r1, g1, b1), (r2, g2, b2), (r3, g3, b3) = (_rgb(p) for p in th)
            self.assertTrue(r1 > 200 and g1 < 60 and b1 < 60)
            self.assertTrue(b2 > 200 and r2 < 60 and g2 < 60)
            self.assertTrue(g3 > 100 and r3 < 60 and b3 < 60)
            m = th[0].stat().st_mtime_ns
            self.assertEqual(make_thumbnails(plan, r), th)                       # idempotent
            self.assertEqual(th[0].stat().st_mtime_ns, m)                        # rien réécrit
            self.assertEqual(sorted(x.suffix for x in th[0].parent.iterdir()), [".jpg"] * 3)  # aucun .part
            sel = plan.model_copy(update={"scenes": [s.model_copy(update={"selected": True}) for s in plan.scenes]})
            self.assertEqual(thumbs_key(sel), thumbs_key(plan))                  # la sélection ne change pas la clé
            self.assertEqual([p.read_bytes() for p in make_thumbnails(sel, r)], [p.read_bytes() for p in th])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            plan = Plan(sources=[Source(id="a", path="inbox/nope.mp4", duration=5.0)],
                        scenes=[Scene(source_id="a", start=0, end=2)])
            with self.assertRaises(PlanError): make_thumbnails(plan, Path(t))
    def test_echec_ffmpeg_donne_none(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t); (r / "inbox").mkdir(); v = r / "inbox" / "s.mp4"
            c = lambda col, d: ["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d={d}:r=25"]
            run_ffmpeg([*c("red", 3), *c("blue", 3), *c("green", 4), "-filter_complex",
                        "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], v)
            plan = Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=10.0)],
                        scenes=[Scene(source_id="a", start=0, end=3), Scene(source_id="a", start=3, end=6),
                                Scene(source_id="a", start=6, end=10)])
            calls: list[Path | None] = []
            def flaky(args, out=None, fmt="mp4", timeout=1800):
                calls.append(out)
                if len(calls) == 2: raise MediaError("boom")
                return run_ffmpeg(args, out, fmt)
            with mock.patch("mt_agent.thumbs.run_ffmpeg", flaky):
                th = make_thumbnails(plan, r)
            self.assertEqual([p is None for p in th], [False, True, False])
            self.assertTrue(th[0].is_file() and th[2].is_file())
            again = make_thumbnails(plan, r)  # reprise : la manquante est générée
            self.assertTrue(all(p is not None and p.is_file() for p in again))
            self.assertEqual(sorted(p.suffix for p in again[0].parent.iterdir()), [".jpg"] * 3)
if __name__ == "__main__": unittest.main()
