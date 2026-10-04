import tempfile, unittest
from pathlib import Path
from mt_agent.approval import approve
from mt_agent.export import export_plan
from mt_agent.models import Plan, Scene, Source
from mt_agent.paths import ensure_outside_inbox, resolve_root

class Paths(unittest.TestCase):
    def test_inbox_guard(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t)
            for bad in (r / "inbox", r / "inbox" / "a.mp4", r / "inbox" / "x" / ".." / "b"):
                with self.assertRaises(PermissionError): ensure_outside_inbox(bad, r)
            (r / "inbox").mkdir(); (r / "link").symlink_to(r / "inbox")
            with self.assertRaises(PermissionError): ensure_outside_inbox(r / "link" / "c", r)
            for ok in (r / "output" / "a", r / "inbox2" / "a", r / "workspace"):
                self.assertEqual(ensure_outside_inbox(ok, r), ok)
    def test_root_from_env(self):
        self.assertEqual(resolve_root({"MT_HOME": "/tmp"}, Path("/x")), Path("/tmp").resolve())
        self.assertEqual(resolve_root({}, Path("/tmp")), Path("/tmp").resolve())
    def test_export_refuses_inbox(self):
        with tempfile.TemporaryDirectory() as t:
            r = Path(t); (r / "inbox").mkdir()
            plan = approve(Plan(sources=[Source(id="a", path="inbox/a.mp4", duration=5.0)],
                                scenes=[Scene(source_id="a", start=0.0, end=2.0, selected=True)]))
            with self.assertRaises(PermissionError): export_plan(plan, r, r / "inbox" / "out")
            self.assertEqual(list((r / "inbox").iterdir()), [])
if __name__ == "__main__": unittest.main()
