import unittest
from mt_agent.approval import PlanError
from mt_agent.compose import compose_plan, letter
from mt_agent.models import Plan, Scene, Source


def _plan(sid, path, dur, spans):
    return Plan(sources=[Source(id=sid, path=path, duration=dur)],
                scenes=[Scene(source_id=sid, start=a, end=b) for a, b in spans])


class ComposeTest(unittest.TestCase):
    def setUp(self):
        self.a = _plan("a", "x.mp4", 10.0, [(0, 3), (3, 6), (6, 9)])
        self.b = _plan("a", "y.mp4", 8.0, [(0, 4), (4, 8)])

    def test_ordre_et_sources(self):
        out = compose_plan([self.a, self.b], [(1, 2), (0, 1), (0, 3)])
        self.assertEqual([s.id for s in out.sources], ["s0", "s1"])
        self.assertEqual([s.path for s in out.sources], ["x.mp4", "y.mp4"])
        self.assertEqual([c.source_id for c in out.scenes], ["s1", "s0", "s0"])
        self.assertEqual([(c.start, c.end) for c in out.scenes], [(4, 8), (0, 3), (6, 9)])
        self.assertTrue(all(c.selected for c in out.scenes))
        self.assertEqual((out.status, out.approved_hash), ("pending_human_review", None))

    def test_ordre_change_le_hash(self):
        h1 = compose_plan([self.a], [(0, 1), (0, 2)]).content_hash()
        h2 = compose_plan([self.a], [(0, 2), (0, 1)]).content_hash()
        self.assertNotEqual(h1, h2)
        self.assertEqual(h1, compose_plan([self.a], [(0, 1), (0, 2)]).content_hash())

    def test_meme_video_fusionnee(self):
        c = _plan("z", "x.mp4", 10.0, [(1, 2)])
        out = compose_plan([self.a, c], [(0, 1), (1, 1)])
        self.assertEqual(len(out.sources), 1)
        self.assertEqual([s.source_id for s in out.scenes], ["s0", "s0"])

    def test_refus(self):
        for plans, order in [([], [(0, 1)]), ([self.a], []), ([self.a], [(0, 1), (0, 1)]),
                             ([self.a], [(0, 4)]), ([self.a, self.b], [(2, 1)])]:
            with self.assertRaises(PlanError):
                compose_plan(plans, order)

    def test_entrees_intactes(self):
        compose_plan([self.a, self.b], [(0, 1), (1, 1)])
        self.assertFalse(self.a.scenes[0].selected)
        self.assertEqual(self.a.sources[0].id, "a")

    def test_lettres(self):
        self.assertEqual([letter(i) for i in (0, 2, 25, 26, 27)], ["A", "C", "Z", "AA", "AB"])


if __name__ == "__main__":
    unittest.main()
