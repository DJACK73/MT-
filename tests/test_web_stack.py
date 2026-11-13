from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HAVE_HTTPX = importlib.util.find_spec("httpx") is not None


@unittest.skipUnless(HAVE_HTTPX, "httpx absent")
class WebStack(unittest.TestCase):
    def setUp(self) -> None:
        import web
        from starlette.testclient import TestClient

        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "inbox").mkdir()
        p = mock.patch.object(web, "ROOT", self.root)
        p.start()
        self.addCleanup(p.stop)
        self.c = TestClient(web.app)

    def _post(self, body: dict) -> object:
        return self.c.post("/api/stack", json=body)

    def test_ancien_format_refuse(self) -> None:
        self.assertEqual(self._post({"a": "x.mp4", "b": "y.mp4", "mode": "cote"}).status_code, 400)

    def test_videos_pas_liste(self) -> None:
        self.assertEqual(self._post({"videos": "a.mp4", "mode": "cote"}).status_code, 400)

    def test_video_absente(self) -> None:
        self.assertEqual(self._post({"videos": ["a.mp4", "b.mp4"], "mode": "cote"}).status_code, 400)

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg absent")
    def test_ok_trois_grille(self) -> None:
        for n in ("a.mp4", "b.mp4"):
            subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=160x120:rate=30:duration=1",
                            "-pix_fmt", "yuv420p", str(self.root / "inbox" / n)], check=True, capture_output=True)
        r = self._post({"videos": ["a.mp4", "b.mp4", "a.mp4"], "mode": "grille", "fit": "remplir"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["out"], "collage/a__b__a-grille-remplir.mp4")
