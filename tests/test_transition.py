import unittest

from mt_agent.approval import PlanError
from mt_agent.export import Look, _join, _trans


class TransitionTest(unittest.TestCase):
    def test_none(self):
        self.assertEqual(_trans(Look(), [4.0, 4.0]), (None, 0.0))
        self.assertEqual(_trans(None, [4.0, 4.0]), (None, 0.0))

    def test_ok(self):
        self.assertEqual(_trans(Look(trans="fade", trans_d=0.5), [4.0, 3.0]), ("fade", 0.5))
        self.assertEqual(_trans(Look(trans="slide"), [4.0, 3.0])[0], "slideleft")

    def test_bounds(self):
        self.assertEqual(_trans(Look(trans="fade", trans_d=0.1), [4.0, 4.0]), ("fade", 0.1))
        self.assertEqual(_trans(Look(trans="fade", trans_d=1.0), [4.0, 4.0]), ("fade", 1.0))
        for bad in (0.05, 1.1):
            with self.assertRaises(PlanError):
                _trans(Look(trans="fade", trans_d=bad), [4.0, 4.0])

    def test_too_long(self):
        with self.assertRaises(PlanError):
            _trans(Look(trans="fade", trans_d=1.0), [4.0, 1.5])

    def test_snap_forbidden(self):
        with self.assertRaises(PlanError):
            _trans(Look(trans="fade", snap_beats=True), [4.0, 4.0])

    def test_join_video(self):
        p = _join([4.0, 3.0, 5.0], "fade", 0.5, False)
        j = ";".join(p)
        self.assertIn("offset=3.500", j)
        self.assertIn("offset=6.000", j)
        self.assertTrue(p[-1].endswith("[out]"))
        self.assertNotIn("concat", j)

    def test_join_audio(self):
        p = _join([4.0, 3.0, 5.0], "fade", 0.5, True)
        self.assertEqual(sum("acrossfade" in x for x in p), 2)
        self.assertTrue(p[-1].endswith("[ac]"))
        self.assertIn("concat", _join([4.0, 3.0], None, 0.0, True)[0])
