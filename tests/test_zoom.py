import unittest
from types import SimpleNamespace

from mt_agent import export as X
from mt_agent.export import Look, _node


class ZoomTest(unittest.TestCase):
    def test_defaut_inchange(self) -> None:
        self.assertEqual(Look().zoom, 1.0)
        self.assertNotIn("crop=trunc", _node(0, 0, 0.0, 3.0, "blur_pad", 1080, 1920))

    def test_crop_avant_scale(self) -> None:
        n = _node(0, 0, 0.0, 3.0, "crop_center", 1080, 1920, zoom=1.5)
        self.assertIn("crop=trunc(iw/1.5/2)*2:trunc(ih/1.5/2)*2", n)
        self.assertLess(n.index("crop=trunc"), n.index("scale="))

    def test_crop_avant_split_fond_flou(self) -> None:
        n = _node(0, 0, 0.0, 3.0, "blur_pad", 1080, 1920, zoom=2.0)
        self.assertLess(n.index("crop=trunc"), n.index("split"))

    def test_validation(self) -> None:
        plan = SimpleNamespace(options=SimpleNamespace(framing="blur_pad"))
        X._look(plan, Look(zoom=2.0))
        for bad in (Look(zoom=0.9), Look(zoom=2.1), Look(fit="none", zoom=1.5)):
            with self.assertRaises(X.PlanError):
                X._look(plan, bad)


if __name__ == "__main__":
    unittest.main()
