import unittest
from types import SimpleNamespace

from mt_agent.approval import PlanError
from mt_agent.export import Look, _check_fx, _fx, _node


class FxTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_fx(None, 1), "")
        self.assertEqual(_fx(Look(), 1), "")

    def test_effect(self):
        self.assertEqual(_fx(Look(fx=frozenset({"bw"})), 1), "hue=s=0")

    def test_fx_only(self):
        lk = Look(fx=frozenset({"bw"}), fx_only=frozenset({2}))
        self.assertEqual(_fx(lk, 1), "")
        self.assertEqual(_fx(lk, 2), "hue=s=0")

    def test_grade_and_order(self):
        self.assertEqual(_fx(Look(bright=0.1, contrast=1.2, sat=1.5), 1),
                         "eq=brightness=0.1:contrast=1.2:saturation=1.5")
        lk = Look(bright=0.1, fx=frozenset({"grain", "bw"}))
        self.assertEqual(_fx(lk, 1), "eq=brightness=0.1:contrast=1:saturation=1,hue=s=0,noise=alls=12:allf=t")

    def test_check_errors(self):
        plan = SimpleNamespace(scenes=[0, 0, 0])
        _check_fx(plan, Look(fx=frozenset({"bw"}), fx_only=frozenset({3})))
        for bad in (Look(bright=0.9), Look(contrast=3.0), Look(sat=3.0),
                    Look(fx=frozenset({"sepia"})), Look(fx=frozenset({"bw"}), fx_only=frozenset({5}))):
            with self.assertRaises(PlanError):
                _check_fx(plan, bad)

    def test_node_inserts_fx(self):
        n = _node(0, 0, 0.0, 4.0, "crop_center", 1080, 1920, fx="hue=s=0")
        self.assertIn("hue=s=0,setsar=1", n)
        n = _node(0, 0, 0.0, 4.0, "bars", 1080, 1920, "black", fx="hue=s=0")
        self.assertIn("color=black,hue=s=0,setsar=1", n)
        n = _node(0, 0, 0.0, 4.0, "none", 1080, 1920, fx="hue=s=0")
        self.assertIn("hue=s=0,format=yuv420p", n)
        self.assertNotIn("hue", _node(0, 0, 0.0, 4.0, "crop_center", 1080, 1920))
