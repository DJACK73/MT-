from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mt_agent import webapi

FF = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
HX = importlib.util.find_spec("httpx") is not None


def _mk(root: Path) -> None:
    (root / "inbox").mkdir()
    (root / "inbox" / "note.txt").write_text("x")
    if FF:
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=30:duration=3",
                        "-pix_fmt", "yuv420p", str(root / "inbox" / "v.mp4")], check=True, capture_output=True)


@unittest.skipUnless(FF, "ffmpeg absent")
class Cut(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        _mk(self.root)

    def test_decoupe_puis_reouverture(self) -> None:
        self.assertEqual(webapi.list_videos(self.root), [{"n": "v.mp4", "cut": False}])
        r1 = webapi.run_cut(self.root, "v.mp4", 0.35, 1.0, None)
        self.assertFalse(r1["reused"])
        self.assertGreaterEqual(r1["scenes"], 1)
        self.assertTrue((self.root / "workspace" / "plans" / r1["name"]).is_file())
        r2 = webapi.run_cut(self.root, "v.mp4", 0.35, 1.0, None)
        self.assertTrue(r2["reused"])
        self.assertEqual(r2["name"], r1["name"])
        self.assertEqual(webapi.list_videos(self.root), [{"n": "v.mp4", "cut": True}])
        r3 = webapi.run_cut(self.root, "v.mp4", 0.5, 1.0, None)
        self.assertFalse(r3["reused"])

    def test_refus(self) -> None:
        for name, mn, mx in (("../v.mp4", 1.0, None), ("note.txt", 1.0, None), ("absent.mp4", 1.0, None),
                             ("v.mp4", 5.0, 2.0), ("v.mp4", 1.0, None)):
            if name == "v.mp4" and mx is None:
                with self.assertRaises(ValueError):
                    webapi.run_cut(self.root, name, 1.5, mn, mx)  # seuil hors ]0,1[
                continue
            with self.assertRaises(ValueError):
                webapi.run_cut(self.root, name, 0.35, mn, mx)


@unittest.skipUnless(HX and FF, "httpx ou ffmpeg absent")
class CutHttp(unittest.TestCase):
    def setUp(self) -> None:
        import web
        from starlette.testclient import TestClient

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        _mk(self.root)
        p = mock.patch.object(web, "ROOT", self.root)
        p.start()
        self.addCleanup(p.stop)
        self.c = TestClient(web.app)

    def test_videos(self) -> None:
        r = self.c.get("/api/videos")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [{"n": "v.mp4", "cut": False}])

    def test_corps_invalide(self) -> None:
        for body in ({}, {"name": "v.mp4"}, {"name": "v.mp4", "threshold": "x", "min": 1},
                     {"name": "v.mp4", "threshold": 0.35, "min": 1, "max": "5"}):
            self.assertEqual(self.c.post("/api/cut", json=body).status_code, 400)

    def test_ok(self) -> None:
        r = self.c.post("/api/cut", json={"name": "v.mp4", "threshold": 0.35, "min": 1, "max": None, "framing": "crop_center"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["reused"])
        self.assertEqual(self.c.get("/api/videos").json(), [{"n": "v.mp4", "cut": True}])
