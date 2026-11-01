import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.approval import PlanError
from mt_agent.export import Look, _cuts, _join, _join_cuts, _total

HAVE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
FADE, NONE = ("fade", 0.5), (None, 0.0)


class CutsTest(unittest.TestCase):
    def test_default_uses_trans(self):
        self.assertEqual(_cuts(Look(trans="fade", trans_d=0.3), [4.0, 4.0, 4.0]), [("fade", 0.3)] * 2)
        self.assertEqual(_cuts(Look(), [4.0, 4.0, 4.0]), [NONE] * 2)
        self.assertEqual(_cuts(None, [4.0, 4.0]), [NONE])
        self.assertEqual(_cuts(Look(trans="fade"), [4.0]), [])

    def test_override(self):
        look = Look(cuts=(("fade", 0.5), ("none", 0.0), ("slide", 0.3)))
        self.assertEqual(_cuts(look, [4.0] * 4), [FADE, NONE, ("slideleft", 0.3)])

    def test_len_mismatch(self):
        with self.assertRaises(PlanError):
            _cuts(Look(cuts=(("fade", 0.5),)), [4.0, 4.0, 4.0])

    def test_neighbors_sum(self):
        look = Look(cuts=(("fade", 1.0), ("fade", 1.0)))
        with self.assertRaises(PlanError):
            _cuts(look, [4.0, 1.5, 4.0])
        self.assertEqual(_cuts(look, [4.0, 2.0, 4.0]), [("fade", 1.0)] * 2)
        with self.assertRaises(PlanError):
            _cuts(Look(cuts=(("fade", 1.0),)), [4.0, 0.9])

    def test_bounds_and_unknown(self):
        for bad in (0.05, 1.1):
            with self.assertRaises(PlanError):
                _cuts(Look(cuts=(("fade", bad),)), [4.0, 4.0])
        with self.assertRaises(PlanError):
            _cuts(Look(cuts=(("zoomin", 0.5),)), [4.0, 4.0])
        self.assertEqual(_cuts(Look(cuts=(("none", 9.0),)), [4.0, 4.0]), [NONE])

    def test_snap_forbidden(self):
        with self.assertRaises(PlanError):
            _cuts(Look(cuts=(("fade", 0.5),), snap_beats=True), [4.0, 4.0])
        self.assertEqual(_cuts(Look(cuts=(("none", 0.0),), snap_beats=True), [4.0, 4.0]), [NONE])

    def test_total(self):
        self.assertAlmostEqual(_total([3.0, 4.0, 5.0], [FADE, NONE]), 11.5)
        self.assertAlmostEqual(_total([3.0, 4.0, 5.0], [NONE, NONE]), 12.0)
        self.assertAlmostEqual(_total([3.0], []), 3.0)

    def test_join_mixed_strings(self):
        j = _join_cuts([4.0, 3.0, 5.0], [FADE, NONE], False)
        s = ";".join(j)
        self.assertIn("offset=3.500", s)
        self.assertIn("concat=n=2:v=1:a=0", s)
        self.assertTrue(j[-1].endswith("[out]"))
        a = _join_cuts([4.0, 3.0, 5.0], [FADE, NONE], True)
        self.assertEqual(sum("acrossfade" in x for x in a), 1)
        self.assertEqual(sum("concat=n=2:v=0:a=1" in x for x in a), 1)
        self.assertTrue(a[-1].endswith("[ac]"))
        k = _join_cuts([4.0, 3.0, 5.0], [NONE, ("slideleft", 0.5)], False)
        self.assertIn("offset=6.500", ";".join(k))

    def test_join_delegates(self):
        d = [4.0, 3.0, 5.0]
        self.assertEqual(_join_cuts(d, [FADE] * 2, True), _join(d, "fade", 0.5, True))
        self.assertEqual(_join_cuts(d, [NONE] * 2, False), _join(d, None, 0.0, False))
        self.assertEqual(_join_cuts([3.0], [], True), _join([3.0], None, 0.0, True))


def _probe(p: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,duration", "-of", "json", str(p)],
                       capture_output=True, text=True, check=True)
    return {s["codec_type"]: float(s["duration"]) for s in json.loads(r.stdout)["streams"]}


@unittest.skipUnless(HAVE, "ffmpeg/ffprobe requis")
class RenderTest(unittest.TestCase):
    def _render(self, durs, cuts, with_a, out):
        ins, nodes = [], []
        for i, d in enumerate(durs):
            col = ("red", "green", "blue")[i % 3]
            vi = i * (2 if with_a else 1)
            ins += ["-f", "lavfi", "-i", f"color=c={col}:s=160x96:r=25:d={d}"]
            nodes.append(f"[{vi}:v]setsar=1,fps=25,format=yuv420p[v{i}]")
            if with_a:
                ins += ["-f", "lavfi", "-i", f"sine=f={300 + 100 * i}:d={d}"]
                nodes.append(f"[{vi + 1}:a]aformat=sample_rates=48000:channel_layouts=stereo[a{i}]")
        graph = ";".join([*nodes, *_join_cuts(durs, cuts, with_a)])
        args = ["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", graph, "-map", "[out]"]
        if with_a:
            args += ["-map", "[ac]", "-c:a", "aac"]
        args += ["-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", str(out)]
        r = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_render_durations(self):
        cases = [([3.0, 3.0, 3.0], [FADE, NONE]),
                 ([3.0, 3.0, 3.0], [NONE, ("slideleft", 0.5)]),
                 ([3.0, 3.0, 3.0], [FADE, ("hblur", 0.3)]),
                 ([3.0, 4.0, 3.0], [FADE] * 2)]
        with tempfile.TemporaryDirectory() as d:
            for k, (durs, cuts) in enumerate(cases):
                for with_a in (False, True):
                    with self.subTest(case=k, audio=with_a):
                        out = Path(d) / f"c{k}{int(with_a)}.mp4"
                        self._render(durs, cuts, with_a, out)
                        got, want = _probe(out), _total(durs, cuts)
                        self.assertAlmostEqual(got["video"], want, delta=0.15)
                        if with_a:
                            self.assertAlmostEqual(got["audio"], want, delta=0.15)


if __name__ == "__main__":
    unittest.main()
