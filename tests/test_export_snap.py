import tempfile, unittest, wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
from mt_agent.approval import PlanError, approve
from mt_agent.export import Look, _snap, export_plan
from mt_agent.ffx import duration, run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

BEATS = {"bpm": 120.0, "beats": [round(0.5 * k, 4) for k in range(200)], "length": 100.0}

def _plan() -> Plan:
    return Plan(options=Options(), sources=[Source(id="a", path="x.mp4", duration=60.0)],
                scenes=[Scene(source_id="a", start=0.0, end=3.4, selected=True),
                        Scene(source_id="a", start=5.0, end=8.0),
                        Scene(source_id="a", start=10.0, end=13.2, selected=True),
                        Scene(source_id="a", start=20.0, end=24.0, selected=True)])

def _wav(path: Path, secs: int = 8, sr: int = 22050) -> None:
    y = (np.sin(2 * np.pi * 440 * np.arange(secs * sr) / sr) * 0.3 * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())

class Snap(unittest.TestCase):
    def test_calage_connu(self):
        p = _plan()
        look = Look(audio="music", music="m.wav", snap_beats=True)
        with patch("mt_agent.export.analyse", return_value=BEATS), patch("mt_agent.export._check_music"):
            q = _snap(p, look, Path("/tmp"))
        for a, b in zip([s.end for s in q.scenes], [3.0, 8.0, 13.0, 24.0]):
            self.assertAlmostEqual(a, b, places=6)
        self.assertEqual([s.start for s in q.scenes], [s.start for s in p.scenes])
        self.assertEqual(p.scenes[0].end, 3.4)  # plan d'origine intact

    def test_sans_calage_plan_identique(self):
        p = _plan()
        self.assertIs(_snap(p, Look(), Path("/tmp")), p)
        self.assertIs(_snap(p, Look(audio="music", music="m.wav"), Path("/tmp")), p)

    def test_exige_musique(self):
        for a in ("none", "source"):
            with self.subTest(audio=a), self.assertRaises(PlanError):
                _snap(_plan(), Look(audio=a, snap_beats=True), Path("/tmp"))

    def test_rythme_non_fiable(self):
        look = Look(audio="music", music="m.wav", snap_beats=True)
        with patch("mt_agent.export.analyse", return_value={"bpm": 0.0, "beats": [], "length": 10.0}), \
                patch("mt_agent.export._check_music"):
            with self.assertRaises(PlanError):
                _snap(_plan(), look, Path("/tmp"))

    def test_snap_lo_invalide(self):
        for lo in (0.0, 11.0):
            with self.subTest(lo=lo), self.assertRaises(PlanError):
                _snap(_plan(), Look(audio="music", music="m.wav", snap_beats=True, snap_lo=lo), Path("/tmp"))

    def test_export_plus_court(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); src = d / "s.mp4"; mus = d / "m.wav"
            run_ffmpeg(["-f", "lavfi", "-i", "testsrc=s=320x240:d=8:r=25", "-pix_fmt", "yuv420p"], src)
            _wav(mus)
            plan = approve(Plan(options=Options(), sources=[Source(id="a", path=str(src), duration=8.0)],
                                scenes=[Scene(source_id="a", start=0.0, end=3.4, selected=True),
                                        Scene(source_id="a", start=4.0, end=7.4, selected=True)]))
            look = Look(audio="music", music=str(mus), snap_beats=True)
            b = {"bpm": 120.0, "beats": [round(0.5 * k, 4) for k in range(40)], "length": 8.0}
            with patch("mt_agent.export.analyse", return_value=b):
                mp4, _ = export_plan(plan, d, d / "o", look=look)
            self.assertAlmostEqual(duration(str(mp4)), 6.0, delta=0.2)  # sans calage : 6,8 s

if __name__ == "__main__": unittest.main()
