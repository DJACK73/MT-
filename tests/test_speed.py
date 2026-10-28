import unittest
from mt_agent import export as ex


class Speed(unittest.TestCase):
    def test_node(self):
        a = ex._node(0, 0, 1.0, 4.0, "bars", 1080, 1920)
        b = ex._node(0, 0, 1.0, 4.0, "bars", 1080, 1920, speed=2.0)
        self.assertIn("setpts=PTS-STARTPTS", a)
        self.assertIn("setpts=(PTS-STARTPTS)/2", b)

    def test_anode(self):
        self.assertNotIn("atempo", ex._anode(0, 0, 1.0, 4.0))
        self.assertIn("atempo=0.5,", ex._anode(0, 0, 1.0, 4.0, 0.5))

    def test_speed_bornes(self):
        self.assertEqual(ex._speed(None), 1.0)
        self.assertEqual(ex._speed(ex.Look(speed=1.5)), 1.5)
        with self.assertRaises(ex.PlanError):
            ex._speed(ex.Look(speed=3.0))
