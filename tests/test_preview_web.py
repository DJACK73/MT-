import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from mt_agent import webapi

try:
    import httpx  # noqa: F401
    from starlette.testclient import TestClient
    import web
except ImportError:
    TestClient = None

PLAN = SimpleNamespace(scenes=[SimpleNamespace(source_id="a", start=1.0, end=4.0)],
                       sources=[SimpleNamespace(id="a", path="inbox/v.mp4")])
OK = dict(kind="video", ratio="9:16", speed=1, quality="normal", audio="none")


class PreviewTest(unittest.TestCase):
    def test_args(self):
        with mock.patch.object(webapi, "_load", return_value=PLAN), \
                mock.patch.object(webapi, "preview_clip", return_value=Path("/r/workspace/previews/x.mp4")) as pc:
            webapi.preview(Path("/r"), "p.json", 1, True, 1.5)
        pc.assert_called_once_with(Path("/r/inbox/v.mp4"), 1.0, 4.0, Path("/r"), mirror=True, speed=1.5)

    def test_bad(self):
        with mock.patch.object(webapi, "_load", return_value=PLAN):
            for n, sp in ((0, 1), (2, 1), (1, 3), (1, float("nan")), (True, 1)):
                with self.assertRaises(ValueError):
                    webapi.preview(Path("/r"), "p.json", n, False, sp)


class MirrorTest(unittest.TestCase):
    def setUp(self):
        webapi._JOB.clear()
        webapi._JOB.update(state="idle")

    def test_bad(self):
        with mock.patch.object(webapi, "_load", return_value=PLAN):
            for m in ("x", [0], [2], ["1"], [True]):
                with self.assertRaises(ValueError):
                    webapi.start_export(Path("/r"), "p.json", mirror=m, **OK)

    def test_passed_to_look(self):
        with mock.patch.object(webapi, "_load", return_value=PLAN), \
                mock.patch.object(webapi, "export_plan", return_value=(Path("/r/o.mp4"), Path("/r/o.json"))) as ep:
            webapi.start_export(Path("/r"), "p.json", mirror=[1], **OK)
            webapi._THREAD.join(5)
        self.assertEqual(ep.call_args.kwargs["look"].mirror_only, frozenset({1}))


@unittest.skipUnless(TestClient, "httpx absent")
class HttpTest(unittest.TestCase):
    def setUp(self):
        self.c = TestClient(web.app)

    def test_preview_400(self):
        for u in ("/api/plan/p.json/preview/0", "/api/plan/p.json/preview/1?speed=9",
                  "/api/plan/p.json/preview/1?speed=abc"):
            r = self.c.get(u)
            self.assertEqual(r.status_code, 400, u)
            self.assertIn("error", r.json())

    def test_export_mirror_400(self):
        r = self.c.post("/api/export", json={"name": "p.json", "kind": "video", "mirror": "x"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("miroir", r.json()["error"])
