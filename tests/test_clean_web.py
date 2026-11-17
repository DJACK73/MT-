import tempfile
import unittest
from pathlib import Path

from mt_agent import webapi
from mt_agent.clean import plan_clean

try:
    import httpx  # noqa: F401
    from starlette.testclient import TestClient
    import web
except ImportError:
    TestClient = None


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.r = Path(self.t.name)
        for d in ("workspace/plans", "workspace/thumbs", "workspace/previews", "output", "inbox"):
            (self.r / d).mkdir(parents=True)
        (self.r / "workspace/plans/a.json").write_text("{}")
        (self.r / "workspace/thumbs/b.jpg").write_bytes(b"xx")
        (self.r / "output/c.mp4").write_bytes(b"yyyy")
        (self.r / "inbox/v.mp4").write_bytes(b"z")
        webapi._JOB.clear()
        webapi._JOB.update(state="idle")

    def tearDown(self):
        self.t.cleanup()

    def test_preview(self):
        p = webapi.clean_preview(self.r, 1)
        self.assertEqual(p["count"], len(plan_clean(self.r, 1)))
        self.assertGreaterEqual(p["count"], 1)
        self.assertGreaterEqual(p["bytes"], 3)

    def test_level1(self):
        res = webapi.do_clean(self.r, 1)
        self.assertEqual(res["errors"], [])
        self.assertFalse((self.r / "workspace/plans/a.json").exists())
        self.assertTrue((self.r / "output/c.mp4").exists())
        self.assertTrue((self.r / "inbox/v.mp4").exists())

    def test_level2(self):
        webapi.do_clean(self.r, 2)
        self.assertFalse((self.r / "output/c.mp4").exists())
        self.assertTrue((self.r / "inbox/v.mp4").exists())

    def test_level3(self):
        (self.r / "inbox/videos").mkdir()
        (self.r / "inbox/videos/v2.mp4").write_bytes(b"zz")
        p = webapi.clean_preview(self.r, 3)
        self.assertEqual(p["count"], len(plan_clean(self.r, 3)))
        webapi.do_clean(self.r, 3)
        self.assertFalse((self.r / "inbox/videos/v2.mp4").exists())
        self.assertTrue((self.r / "inbox/videos").is_dir())
        self.assertTrue((self.r / "inbox/v.mp4").exists())

    def test_level4_refused(self):
        for fn in (webapi.clean_preview, webapi.do_clean):
            with self.assertRaises(ValueError):
                fn(self.r, 4)

    def test_busy(self):
        webapi._JOB.update(state="running")
        with self.assertRaises(webapi.PlanError):
            webapi.do_clean(self.r, 1)
        self.assertTrue((self.r / "workspace/plans/a.json").exists())


@unittest.skipUnless(TestClient, "httpx absent")
class HttpTest(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(web.app)

    def test_preview(self):
        r = self.c.get("/api/clean/1")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(set(r.json()), {"level", "count", "bytes"})

    def test_level_refused(self):
        self.assertEqual(self.c.get("/api/clean/4").status_code, 400)
        self.assertEqual(self.c.post("/api/clean/4", json={"confirm": 4}).status_code, 400)

    def test_post_needs_confirm(self):
        self.assertEqual(self.c.post("/api/clean/1", json={}).status_code, 400)
        self.assertEqual(self.c.post("/api/clean/1", json={"confirm": 2}).status_code, 400)
        self.assertEqual(self.c.post("/api/clean/1", json={"confirm": True}).status_code, 400)
