import random, unittest
from mt_agent.fit import split_long

class Fit(unittest.TestCase):
    def _eq(self, got, want):
        self.assertEqual(len(got), len(want))
        for g, w in zip(got, want):
            self.assertAlmostEqual(g[0], w[0]); self.assertAlmostEqual(g[1], w[1])

    def test_known(self):
        self._eq(split_long([(0, 5)], 3, 5), [(0, 5)])
        self._eq(split_long([(0, 5.5)], 3, 5), [(0, 5.5)])         # zone impossible : gardée
        self._eq(split_long([(0, 6)], 3, 5), [(0, 3), (3, 6)])
        self._eq(split_long([(0, 10)], 3, 5), [(0, 5), (5, 10)])
        self._eq(split_long([(2, 10.5)], 3, 4), [(2, 6.25), (6.25, 10.5)])
        r = split_long([(0, 28.77)], 3, 5)
        self.assertEqual(len(r), 6); self.assertAlmostEqual(r[-1][1], 28.77)

    def test_invalid(self):
        with self.assertRaises(ValueError): split_long([(0, 5)], 5, 3)

    def test_random(self):
        rnd = random.Random(7)
        for _ in range(2000):
            mn = rnd.uniform(1, 4); mx = rnd.uniform(mn, 8); d = rnd.uniform(mn, 40)
            r = split_long([(1.0, 1.0 + d)], mn, mx)
            self.assertAlmostEqual(r[0][0], 1.0); self.assertAlmostEqual(r[-1][1], 1.0 + d)
            for p, q in zip(r, r[1:]): self.assertAlmostEqual(p[1], q[0])
            for a, b in r:
                self.assertGreaterEqual(b - a, mn - 1e-9)
                self.assertTrue(b - a <= mx + 1e-9 or b - a < 2 * mn)
