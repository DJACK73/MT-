import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.avtools import extract_audio, remove_audio
from mt_agent.ffx import MediaError

HAVE = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def _kinds(p: Path) -> list[str]:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True, check=True)
    return sorted(x for x in r.stdout.split() if x)


@unittest.skipUnless(HAVE, "ffmpeg/ffprobe absents")
class AvTools(unittest.TestCase):
    def setUp(self) -> None:
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.dir = Path(d.name)
        self.src = self.dir / "a.mp4"
        subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error",
                        "-f", "lavfi", "-i", "testsrc=size=64x64:rate=10:duration=1",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(self.src)],
                       check=True, capture_output=True)

    def test_extract_audio_only(self) -> None:
        out = self.dir / "a.m4a"
        extract_audio(self.src, out)
        self.assertEqual(_kinds(out), ["audio"])

    def test_remove_audio_keeps_video(self) -> None:
        out = self.dir / "muet.mp4"
        remove_audio(self.src, out)
        self.assertEqual(_kinds(out), ["video"])

    def test_refuses_overwrite(self) -> None:
        out = self.dir / "x.m4a"
        out.write_bytes(b"x")
        with self.assertRaises(MediaError):
            extract_audio(self.src, out)
        self.assertEqual(out.read_bytes(), b"x")
