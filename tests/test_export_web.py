import unittest
from pathlib import Path
from unittest import mock

from mt_agent import webapi

try:
    import httpx  # noqa: F401
    from starlette.testclient import TestClient
    import web
except ImportError:
    TestClient = None

OK = dict(kind="video", ratio="9:16", speed=1, quality="normal", audio="none")


class ServiceTest(unittest.TestCase):
    def setUp(self):
        webapi._JOB.clear()
        webapi._JOB.update(state="idle")

    def run_job(self, **kw):
        with mock.patch.object(webapi, "_load", return_value=object()):
            webapi.start_export(Path("/r"), "p.json", **{**OK, **kw})
        webapi._THREAD.join(5)
        return webapi.get_job()

    def test_validation(self):
        for bad in ({"kind": "x"}, {"ratio": "4:3"}, {"speed": 3}, {"quality": "?"}, {"audio": "music"}):
            with self.assertRaises(ValueError):
                webapi.start_export(Path("/nope"), "p.json", **{**OK, **bad})

    def test_done(self):
        with mock.patch.object(webapi, "export_plan", return_value=(Path("/r/output/assemble/a.mp4"), Path("/r/x.json"))):
            j = self.run_job()
        self.assertEqual(j["state"], "done")
        self.assertEqual(j["files"], ["output/assemble/a.mp4"])

    def test_error(self):
        with mock.patch.object(webapi, "export_plan", side_effect=webapi.PlanError("non approuve")):
            j = self.run_job()
        self.assertEqual((j["state"], j["error"]), ("error", "non approuve"))

    def test_busy(self):
        webapi._JOB.update(state="running")
        with mock.patch.object(webapi, "_load", return_value=object()):
            with self.assertRaises(webapi.PlanError):
                webapi.start_export(Path("/r"), "p.json", **OK)


@unittest.skipUnless(TestClient, "httpx absent")
class HttpTest(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(web.app)

    def test_job_idle(self):
        webapi._JOB.clear()
        webapi._JOB.update(state="idle")
        r = self.c.get("/api/job")
        self.assertEqual((r.status_code, r.json()["state"]), (200, "idle"))

    def test_export_400(self):
        r = self.c.post("/api/export", json={"name": "p.json", "kind": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("error", r.json())
        self.assertEqual(self.c.post("/api/export", json={}).status_code, 400)
