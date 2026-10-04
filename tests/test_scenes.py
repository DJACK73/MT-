import random, unittest
from mt_agent.scenes import merge_short

class MergeShort(unittest.TestCase):
    def test_known_answers(self):
        self.assertEqual(merge_short([], 10, 1), [(0, 10)])
        self.assertEqual(merge_short([3, 6], 10, 1), [(0, 3), (3, 6), (6, 10)])
        self.assertEqual(merge_short([0.5], 10, 1), [(0, 10)])          # début court absorbé
        self.assertEqual(merge_short([9.5], 10, 1), [(0, 10)])          # fin courte absorbée
        self.assertEqual(merge_short([3, 3.4, 6], 10, 1), [(0, 3.4), (3.4, 6), (6, 10)])
        self.assertEqual(merge_short([6, 3, 3, -1, 11], 10, 1), [(0, 3), (3, 6), (6, 10)])  # désordre, doublon, hors borne
        self.assertEqual(merge_short([], 0.5, 1), [(0, 0.5)])           # vidéo plus courte que min_s
    def test_invalid(self):
        with self.assertRaises(ValueError): merge_short([], 0, 1)
    def test_properties(self):
        rnd = random.Random(7)
        for _ in range(2000):
            total, min_s = rnd.uniform(0.1, 60), rnd.uniform(0, 5)
            spans = merge_short([rnd.uniform(-1, total + 1) for _ in range(rnd.randint(0, 80))], total, min_s)
            self.assertEqual(spans[0][0], 0); self.assertEqual(spans[-1][1], total)
            for (a, b), (c, d) in zip(spans, spans[1:]): self.assertEqual(b, c)
            if total >= min_s:
                self.assertTrue(all(b - a >= min_s - 1e-6 for a, b in spans))
if __name__ == "__main__": unittest.main()
