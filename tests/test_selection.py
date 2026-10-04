import contextlib, io, tempfile, unittest
from pathlib import Path
from mt_agent.approval import PlanError, approve, is_approved, save_plan
from mt_agent.cmd import main
from mt_agent.models import Plan, Scene, Source
from mt_agent.selection import parse_selection, select_scenes

def _plan(n: int = 5) -> Plan:
    return Plan(sources=[Source(id="a", path="x.mp4", duration=float(n))],
                scenes=[Scene(source_id="a", start=float(i), end=float(i + 1), selected=True) for i in range(n)])

class Selection(unittest.TestCase):
    def test_parse_known_answers(self):
        self.assertEqual(parse_selection("1-3,5", 5), {1, 2, 3, 5})
        self.assertEqual(parse_selection(" 2 , 2-2 ", 5), {2})
        for bad in ("", "0", "6", "3-2", "a", "1,", "-1", "2-", "1-9"):
            with self.subTest(bad=bad), self.assertRaises(PlanError): parse_selection(bad, 5)
    def test_select_resets_approval(self):
        a = approve(_plan()); self.assertTrue(is_approved(a))
        s = select_scenes(a, "2,4")
        self.assertEqual([x.selected for x in s.scenes], [False, True, False, True, False])
        self.assertEqual((s.status, s.approved_hash), ("pending_human_review", None))
        self.assertTrue(is_approved(a))                       # original intact
        with self.assertRaises(PlanError): select_scenes(a.model_copy(update={"status": "rendered"}), "1")
    def test_cli(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t); f = save_plan(_plan(), r / "plans")
            def run(argv):
                o, e = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(o), contextlib.redirect_stderr(e):
                    return main(argv, r), o.getvalue().strip()
            code, out = run(["select", str(f), "1-2"])
            self.assertEqual(code, 0)
            self.assertEqual([x.selected for x in Plan.model_validate_json(Path(out).read_text()).scenes], [True, True, False, False, False])
            code, listing = run(["scenes", out])
            self.assertEqual((code, len(listing.splitlines())), (0, 5))
            self.assertEqual(run(["select", str(f), "1-2"])[0], 1)   # même sélection : refus d'écraser
            self.assertEqual(run(["select", str(f), "9"])[0], 1)
if __name__ == "__main__": unittest.main()
