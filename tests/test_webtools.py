import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent import webapi
from mt_agent.ffx import MediaError

HAVE = bool(shutil.which("ffmpeg"))


class WebTools(unittest.TestCase):
    def setUp(self) -> None:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        inbox = self.root / "inbox"
        inbox.mkdir()
        (inbox / "a.mp4:Zone.Identifier").write_text("x")
        (inbox / "notes.txt").write_text("x")
        if HAVE:
            subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
                            "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10:duration=1",
                            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(inbox / "a.mp4")],
                           check=True, capture_output=True)
        else:
            (inbox / "a.mp4").write_bytes(b"x")

    def test_list_inbox_only_videos(self) -> None:
        self.assertEqual(webapi.list_inbox(self.root), ["a.mp4"])

    def test_bad_names_refused(self) -> None:
        for n in ("../a.mp4", "notes.txt", "absent.mp4", ""):
            with self.assertRaises(ValueError):
                webapi.run_tool(self.root, n, "audio")
        with self.assertRaises(ValueError):
            webapi.run_tool(self.root, "a.mp4", "zzz")

    @unittest.skipUnless(HAVE, "ffmpeg absent")
    def test_audio_and_muet_in_output(self) -> None:
        self.assertEqual(webapi.run_tool(self.root, "a.mp4", "audio")["out"], "a.m4a")
        self.assertEqual(webapi.run_tool(self.root, "a.mp4", "muet")["out"], "a-muet.mp4")
        self.assertTrue((self.root / "output" / "a.m4a").is_file())
        self.assertTrue((self.root / "output" / "a-muet.mp4").is_file())
        self.assertEqual(webapi.list_inbox(self.root), ["a.mp4"])

    @unittest.skipUnless(HAVE, "ffmpeg absent")
    def test_no_overwrite(self) -> None:
        webapi.run_tool(self.root, "a.mp4", "audio")
        with self.assertRaises(MediaError):
            webapi.run_tool(self.root, "a.mp4", "audio")
