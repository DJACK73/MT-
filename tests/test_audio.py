import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.approval import PlanError
from mt_agent.export import Look, _afilter, _audio
from mt_agent.ffx import has_audio


class AudioTests(unittest.TestCase):
    def test_afilter_simple(self):
        self.assertEqual(_afilter(4.0), "afade=t=in:d=0.02,afade=t=out:st=3.980:d=0.02")

    def test_afilter_gain(self):
        self.assertEqual(_afilter(4.0, -6.0),
                         "volume=-6dB,afade=t=in:d=0.02,afade=t=out:st=3.980:d=0.02")

    def test_afilter_court(self):
        self.assertEqual(_afilter(0.02), "afade=t=in:d=0.01,afade=t=out:st=0.010:d=0.01")

    def test_audio_defaut(self):
        self.assertEqual(_audio(None), (False, 0.0))
        self.assertEqual(_audio(Look()), (False, 0.0))

    def test_audio_source(self):
        self.assertEqual(_audio(Look(audio="source", audio_db=-6.0)), (True, -6.0))

    def test_audio_refus(self):
        with self.assertRaises(PlanError):
            _audio(Look(audio="x"))
        with self.assertRaises(PlanError):
            _audio(Look(audio="source", audio_db=99.0))

    def test_has_audio(self):
        with tempfile.TemporaryDirectory() as d:
            muet, son = Path(d) / "m.mp4", Path(d) / "s.mp4"
            base = ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=d=0.5:s=64x64"]
            subprocess.run([*base, "-c:v", "libx264", str(muet)], check=True)
            subprocess.run([*base, "-f", "lavfi", "-i", "sine=d=0.5", "-shortest",
                            "-c:v", "libx264", "-c:a", "aac", str(son)], check=True)
            self.assertFalse(has_audio(str(muet)))
            self.assertTrue(has_audio(str(son)))


if __name__ == "__main__":
    unittest.main()
