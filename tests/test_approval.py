import tempfile, unittest
from pathlib import Path
from mt_agent.approval import PlanError, approve, assert_renderable, is_approved, plan_id, save_plan
from mt_agent.models import Plan, Scene, Source

def _plan() -> Plan:
    return Plan(sources=[Source(id="a", path="inbox/a.mp4", duration=10.0)],
                scenes=[Scene(source_id="a", start=0.0, end=4.0), Scene(source_id="a", start=4.0, end=10.0)])

class Approval(unittest.TestCase):
    def test_known_answers(self):
        p = _plan()
        self.assertFalse(is_approved(p))
        with self.assertRaises(PlanError): assert_renderable(p)
        a = approve(p)
        self.assertTrue(is_approved(a)); assert_renderable(a)
        self.assertEqual(plan_id(p), plan_id(a))              # statut hors du hash
        self.assertEqual(p.status, "pending_human_review")    # original intact
        self.assertIsNone(p.approved_hash)
    def test_edit_invalidates(self):
        a = approve(_plan())
        b = a.model_copy(update={"scenes": [a.scenes[0].model_copy(update={"end": 5.0}), a.scenes[1]]})
        self.assertFalse(is_approved(b)); self.assertNotEqual(plan_id(a), plan_id(b))
        with self.assertRaises(PlanError): assert_renderable(b)
    def test_rendered_cannot_be_approved(self):
        with self.assertRaises(PlanError): approve(_plan().model_copy(update={"status": "rendered"}))
    def test_save_never_overwrites(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); p = _plan()
            f1, f2 = save_plan(p, d), save_plan(approve(p), d)
            self.assertNotEqual(f1, f2)
            with self.assertRaises(PlanError): save_plan(p, d)
            self.assertEqual(Plan.model_validate_json(f2.read_text()), approve(p))
            self.assertEqual(sorted(x.name for x in d.iterdir()), sorted([f1.name, f2.name]))  # aucun .part
if __name__ == "__main__": unittest.main()
