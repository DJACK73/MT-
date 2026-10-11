import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from mt_agent.lab.beats_select import synth
from mt_agent.rhythm import SR, analyse, grid_from_pcm, loop_beats, snap_durations

class Rhythm(unittest.TestCase):
    def test_grille_metronome(self):
        for bpm in (90, 120, 140):
            with self.subTest(bpm=bpm):
                y, truth = synth(bpm)
                c, g = grid_from_pcm(y)
                self.assertAlmostEqual(c, bpm, delta=0.5)
                g, t = np.asarray(g), np.asarray(truth)
                d = np.abs(g[np.abs(t[:, None] - g[None, :]).argmin(axis=1)] - t)
                self.assertLessEqual(float(d.max()), 0.040)  # une image à 25 fps

    def test_silence(self):
        self.assertEqual(grid_from_pcm(np.zeros(SR * 10, dtype=np.float32)), (0.0, []))

    def test_loop_beats(self):
        self.assertEqual(loop_beats([0.5, 1.0, 1.5], 2.0, 0.0, 5.0), [0.5, 1.0, 1.5, 2.5, 3.0, 3.5, 4.5])
        self.assertEqual(loop_beats([0.5, 1.0, 1.5], 2.0, 0.75, 5.0),
                         [0.25, 0.75, 1.75, 2.25, 2.75, 3.75, 4.25, 4.75])
        self.assertEqual(loop_beats([], 2.0, 0.0, 5.0), [])

    def test_snap_connu(self):
        beats = [float(x) for x in np.arange(0.0, 12.0, 0.5)]
        got = snap_durations([3.4, 3.2, 4.0], beats, 3.0)
        for a, b in zip(got, [3.0, 3.0, 4.0]):
            self.assertAlmostEqual(a, b, places=6)

    def test_snap_limites(self):
        self.assertEqual(snap_durations([3.2], [0.1, 5.0], 3.0), [3.2])  # aucun battement dans [3.0 ; 3.2]
        self.assertEqual(snap_durations([2.0], [0.5, 1.5, 2.0], 3.0), [2.0])  # scène sous le minimum : intacte
        durs = [3.9, 4.4, 3.1, 5.0]
        got = snap_durations(durs, [float(x) for x in np.arange(0.0, 20.0, 0.37)], 3.0)
        self.assertTrue(all(3.0 - 1e-6 <= g <= d + 1e-6 for g, d in zip(got, durs)))

    def test_cache(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); f = d / "m.wav"; f.write_bytes(b"abc")
            with patch("mt_agent.rhythm._compute", return_value=(120.0, [0.5, 1.0], 2.0)) as m:
                a = analyse(f, d / "cache")
                b = analyse(f, d / "cache")
                self.assertEqual(a, b)
                self.assertEqual(a, {"bpm": 120.0, "beats": [0.5, 1.0], "length": 2.0})
                self.assertEqual(m.call_count, 1)
                f.write_bytes(b"abcd")  # contenu changé : nouvelle clé, recalcul
                analyse(f, d / "cache")
                self.assertEqual(m.call_count, 2)
            self.assertEqual(len(list((d / "cache").glob("*.part"))), 0)
if __name__ == "__main__": unittest.main()
