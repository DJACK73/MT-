import unittest

from mt_agent.manual import parse_spans, parse_time, plan_from_spans, whole_spans


class Manual(unittest.TestCase):
    def test_temps(self) -> None:
        self.assertEqual(parse_time("12.5", 60), 12.5)
        self.assertEqual(parse_time("12,5", 60), 12.5)
        self.assertEqual(parse_time("1:02.5", 90), 62.5)
        self.assertEqual(parse_time("1:02:03", 9999), 3723.0)
        self.assertEqual(parse_time("fin", 42.0), 42.0)

    def test_temps_invalides(self) -> None:
        for bad in ("", "abc", "nan", "inf", "-5", "1:2:3:4", "1e3"):
            with self.assertRaises(ValueError, msg=bad):
                parse_time(bad, 60)

    def test_plages(self) -> None:
        self.assertEqual(parse_spans("12.5-16\n20 - 25,5 ; 1:00-fin", 70.0),
                         [(12.5, 16.0), (20.0, 25.5), (60.0, 70.0)])

    def test_ordre_conserve(self) -> None:
        self.assertEqual(parse_spans("30-35\n5-8", 60.0), [(30.0, 35.0), (5.0, 8.0)])

    def test_plages_invalides(self) -> None:
        for bad in ("", "  \n ", "5", "5-", "-5-10", "10-5", "5-5", "0-61", "a-b"):
            with self.assertRaises(ValueError, msg=bad):
                parse_spans(bad, 60.0)

    def test_plan(self) -> None:
        p = plan_from_spans("inbox/x.mp4", 60.0, parse_spans("1-4;10-14", 60.0))
        self.assertEqual([(s.start, s.end, s.selected) for s in p.scenes], [(1.0, 4.0, True), (10.0, 14.0, True)])
        self.assertIsNone(p.options.max_scene_seconds)
        q = plan_from_spans("inbox/x.mp4", 60.0, parse_spans("1-4;10-14", 60.0))
        self.assertEqual(p.content_hash(), q.content_hash())

    def test_entiere(self) -> None:
        self.assertEqual(whole_spans(12.3456), [(0.0, 12.346)])


if __name__ == "__main__":
    unittest.main()
