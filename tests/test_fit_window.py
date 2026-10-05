import random, unittest
from mt_agent.fit import _feasible, fit_window

class FitWindow(unittest.TestCase):
    def _eq(self, got, want):
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertAlmostEqual(g[0], w[0]); self.assertAlmostEqual(g[1], w[1])

    def test_known(self):
        self._eq(fit_window([0, 5], 3, 5), [(0, 5)])
        self._eq(fit_window([0, 5.5], 3, 5), [(0, 5.5)])                 # zone impossible : gardée
        self._eq(fit_window([0, 2], 3, 5), [(0, 2)])                     # plus courte que min : gardée
        self._eq(fit_window([0, 12], 3, 5), [(0, 4), (4, 8), (8, 12)])   # aucune borne : parts égales
        self._eq(fit_window([0, 2, 4, 6, 8, 10], 3, 5), [(0, 4), (4, 7), (7, 10)])
        self._eq(fit_window([0, 3, 4.5, 8, 10], 3, 5), [(0, 3), (3, 6.5), (6.5, 10)])
        self._eq(fit_window([0, 3, 6, 9, 12, 15], 3, 5), [(0, 3), (3, 6), (6, 9), (9, 12), (12, 15)])

    def test_invalid(self):
        for args in (([0, 5], 5, 3), ([0], 3, 5), ([0, 5, 4], 3, 5), ([0, 5, 5], 3, 5)):
            with self.assertRaises(ValueError): fit_window(*args)

    def test_random(self):
        rnd = random.Random(11)
        for _ in range(3000):
            mn = rnd.uniform(1, 4); mx = rnd.uniform(mn, 8); t = rnd.uniform(mn, 60)
            bs = sorted({0.0, t, *(rnd.uniform(0, t) for _ in range(rnd.randint(0, 40)))})
            bs = [b for i, b in enumerate(bs) if i == 0 or b - bs[i - 1] > 1e-6]
            if len(bs) < 2: continue
            r = fit_window(bs, mn, mx); total = bs[-1] - bs[0]
            self.assertAlmostEqual(r[0][0], bs[0]); self.assertAlmostEqual(r[-1][1], bs[-1])
            for p, q in zip(r, r[1:]): self.assertAlmostEqual(p[1], q[0])
            for a, b in r: self.assertGreaterEqual(b - a, min(mn, total) - 1e-6)
            if total <= mx or _feasible(total, mn, mx):
                for a, b in r: self.assertLessEqual(b - a, mx + 1e-6)
