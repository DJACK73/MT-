import tempfile
import unittest
from pathlib import Path
from mt_agent import webapi
from mt_agent.approval import PlanError, save_plan
from mt_agent.models import Plan, Scene, Source


def _plan(root, sel):
    plan = Plan(sources=[Source(id="a", path="x.mp4", duration=20.0)],
                scenes=[Scene(source_id="a", start=i * 4.0, end=i * 4.0 + 4.0, selected=s) for i, s in enumerate(sel)])
    return save_plan(plan, root / "workspace" / "plans").name


class WebApiTest(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.root = Path(self._t.name)

    def test_list_and_get(self):
        name = _plan(self.root, [True, True, False, False])
        lst = webapi.list_plans(self.root)
        self.assertEqual(len(lst), 1)
        self.assertEqual(lst[0]["selected"], 2)
        v = webapi.get_plan(self.root, name)
        self.assertEqual(len(v["scenes"]), 4)
        self.assertEqual(v["order"], [1, 2])
        self.assertAlmostEqual(v["kept_seconds"], 8.0)
        self.assertEqual(v["scenes"][0]["rank"], 1)
        self.assertIsNone(v["scenes"][2]["rank"])

    def test_apply_changes_creates_new_plan(self):
        old = _plan(self.root, [True, True, False, False])
        r = webapi.apply_selection(self.root, old, [3, 1])
        self.assertTrue(r["changed"])
        self.assertNotEqual(r["name"], old)
        self.assertTrue((self.root / "workspace" / "plans" / old).is_file())
        self.assertEqual(webapi.get_plan(self.root, r["name"])["order"], [3, 1])

    def test_apply_same_selection_changes_nothing(self):
        old = _plan(self.root, [True, True, False, False])
        r = webapi.apply_selection(self.root, old, [1, 2])
        self.assertFalse(r["changed"])
        self.assertEqual(r["name"], old)

    def test_apply_rejects_empty_and_out_of_range(self):
        old = _plan(self.root, [True, True, False, False])
        for bad in ([], [9]):
            with self.assertRaises(PlanError):
                webapi.apply_selection(self.root, old, bad)

    def test_approve(self):
        old = _plan(self.root, [True, True, False, False])
        v = webapi.get_plan(self.root, webapi.approve_plan(self.root, old)["name"])
        self.assertTrue(v["approved"])
        self.assertEqual(v["status"], "approved")

    def test_bad_name_rejected(self):
        for bad in ("../x.json", "a/b.json", "nope.json"):
            with self.assertRaises(PlanError):
                webapi.get_plan(self.root, bad)
