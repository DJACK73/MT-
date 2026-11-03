import unittest
from mt_agent.approval import PlanError, approve, is_approved
from mt_agent.models import Plan, Scene, Source
from mt_agent.selection import parse_order, parse_selection, select_scenes

def _plan(n: int = 5) -> Plan:
    return Plan(sources=[Source(id="a", path="x.mp4", duration=float(n))],
                scenes=[Scene(source_id="a", start=float(i), end=float(i + 1), selected=True) for i in range(n)])

class Order(unittest.TestCase):
    def test_parse_order_keeps_input_order(self):
        self.assertEqual(parse_order("3,1-2", 5), [3, 1, 2])
        self.assertEqual(parse_order("2,2,1-3", 5), [2, 1, 3])
        self.assertEqual(parse_selection("3,1-2", 5), {1, 2, 3})
        with self.assertRaises(PlanError): parse_order("1,9", 5)
    def test_select_reorders_when_not_ascending(self):
        a = approve(_plan()); s = select_scenes(a, "4,2")
        self.assertEqual([x.start for x in s.scenes], [3.0, 1.0, 0.0, 2.0, 4.0])
        self.assertEqual([x.selected for x in s.scenes], [True, True, False, False, False])
        self.assertEqual((s.status, s.approved_hash), ("pending_human_review", None))
        Plan.model_validate(s.model_dump())
        self.assertNotEqual(s.content_hash(), a.content_hash())
        self.assertTrue(is_approved(a))
    def test_select_ascending_keeps_positions(self):
        s = select_scenes(_plan(), "2,4")
        self.assertEqual([x.start for x in s.scenes], [0.0, 1.0, 2.0, 3.0, 4.0])
        self.assertEqual([x.selected for x in s.scenes], [False, True, False, True, False])
if __name__ == "__main__": unittest.main()
