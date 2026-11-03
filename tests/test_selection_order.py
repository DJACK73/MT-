import unittest
from mt_agent.approval import PlanError, approve, is_approved
from mt_agent.export import build_graph
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
    def test_select_keeps_positions_sets_order(self):
        a = approve(_plan()); s = select_scenes(a, "4,2")
        self.assertEqual([x.start for x in s.scenes], [0.0, 1.0, 2.0, 3.0, 4.0])
        self.assertEqual([x.selected for x in s.scenes], [False, True, False, True, False])
        self.assertEqual((s.order, s.status, s.approved_hash), ([4, 2], "pending_human_review", None))
        self.assertTrue(is_approved(a))
    def test_select_ascending_clears_order(self):
        s = select_scenes(select_scenes(_plan(), "4,2"), "2,4")
        self.assertEqual(s.order, [])
        self.assertEqual([n for n, _ in s.chosen()], [2, 4])
    def test_chosen_and_hash(self):
        asc, rev = select_scenes(_plan(), "2,4"), select_scenes(_plan(), "4,2")
        self.assertEqual([(n, x.start) for n, x in rev.chosen()], [(4, 3.0), (2, 1.0)])
        self.assertNotEqual(asc.content_hash(), rev.content_hash())
        back = Plan.model_validate_json(rev.model_dump_json())
        self.assertEqual(back.order, [4, 2])
        self.assertEqual(approve(rev).order, [4, 2]); self.assertTrue(is_approved(approve(rev)))
    def test_graph_follows_order(self):
        asc, rev = select_scenes(_plan(), "2,4"), select_scenes(_plan(), "4,2")
        self.assertNotEqual(build_graph(asc)[1], build_graph(rev)[1])
if __name__ == "__main__": unittest.main()
