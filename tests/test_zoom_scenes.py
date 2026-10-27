import unittest
from types import SimpleNamespace

from mt_agent import export as X
from mt_agent.export import Look


class ZoomScenes(unittest.TestCase):
    def test_zoom_par_scene(self) -> None:
        self.assertEqual(X._zoom(None, 1), 1.0)
        self.assertEqual(X._zoom(Look(zoom=1.5), 3), 1.5)  # zoom_only=None : toutes les scènes
        look = Look(zoom=1.5, zoom_only=frozenset({2}))
        self.assertEqual((X._zoom(look, 1), X._zoom(look, 2)), (1.0, 1.5))

    def test_bornes(self) -> None:
        plan = SimpleNamespace(scenes=[1, 2, 3])
        X._check_zoom(plan, Look(zoom=1.5, zoom_only=frozenset({3})))
        with self.assertRaises(X.PlanError):
            X._check_zoom(plan, Look(zoom=1.5, zoom_only=frozenset({4})))


if __name__ == "__main__":
    unittest.main()
