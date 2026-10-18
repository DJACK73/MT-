import unittest
from types import SimpleNamespace
from mt_agent.approval import PlanError
from mt_agent.export import Look, _check_mirror, _flip


class MirrorScenes(unittest.TestCase):
    def test_flip(self) -> None:
        look = Look(mirror_only=frozenset({2, 4}))
        self.assertEqual([_flip(look, n) for n in (1, 2, 3, 4)], [False, True, False, True])
        self.assertTrue(_flip(Look(mirror=True), 1))
        self.assertFalse(_flip(Look(), 1))
        self.assertFalse(_flip(None, 1))

    def test_hors_limites(self) -> None:
        plan = SimpleNamespace(scenes=[0, 0, 0])
        _check_mirror(plan, None)
        _check_mirror(plan, Look(mirror_only=frozenset({1, 3})))
        for bad in ({0}, {4}):
            with self.assertRaises(PlanError):
                _check_mirror(plan, Look(mirror_only=frozenset(bad)))


if __name__ == "__main__":
    unittest.main()
