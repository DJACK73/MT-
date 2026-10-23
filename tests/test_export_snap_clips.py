import tempfile, unittest, wave
from pathlib import Path
from unittest.mock import patch
import numpy as np
from mt_agent.approval import PlanError, approve
from mt_agent.export import Look, _clip_snap, export_clips
from mt_agent.ffx import duration, run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

BEATS = {"bpm": 120.0, "beats": [round(0.5 * k, 4) for k in range(200)], "length": 100.0}

def _wav(path: Path, secs: int = 8, sr: int = 22050) -> None:
    y = (np.sin(2 * np.pi * 440 * np.arange(secs * sr) / sr) * 0.3 * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())

class SnapClips(unittest.TestCase):
    def _run(self, look: Look, durs: list[float]) -> list[float]:
        with patch("mt_agent.export.analyse", return_value=BEATS), patch("mt_agent.export._check_music"):
            return _clip_snap(look, Path("/tmp"), durs)

    def test_connu(self):
        got = self._run(Look(audio="music", music="m.wav", snap_clips=True), [3.4, 3.2, 4.2, 2.0])
        for a, b in zip(got, [3.0, 3.0, 4.0, 2.0]):  # 2.0 : sous le minimum, intact
            self.assertAlmostEqual(a, b, places=6)

    def test_depart_dans_le_morceau(self):
        got = self._run(Look(audio="music", music="m.wav", snap_clips=True, music_start=0.25), [3.4])
        self.assertAlmostEqual(got[0], 3.25, places=6)

    def test_inactif_meme_liste(self):
        durs = [3.4, 4.0]
        self.assertIs(_clip_snap(Look(), Path("/tmp"), durs), durs)
        self.assertIs(_clip_snap(Look(audio="music", music="m.wav"), Path("/tmp"), durs), durs)

    def test_exige_musique(self):
        for a in ("none", "source"):
            with self.subTest(audio=a), self.assertRaises(PlanError):
                _clip_snap(Look(audio=a, snap_clips=True), Path("/tmp"), [3.4])

    def test_export_clips_cales(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t); src = d / "s.mp4"; mus = d / "m.wav"
            run_ffmpeg(["-f", "lavfi", "-i", "testsrc=s=320x240:d=8:r=25", "-pix_fmt", "yuv420p"], src)
            _wav(mus)
            plan = approve(Plan(options=Options(), sources=[Source(id="a", path=str(src), duration=8.0)],
                                scenes=[Scene(source_id="a", start=0.0, end=3.4, selected=True),
                                        Scene(source_id="a", start=4.0, end=7.4, selected=True)]))
            look = Look(audio="music", music=str(mus), snap_clips=True)
            b = {"bpm": 120.0, "beats": [round(0.5 * k, 4) for k in range(40)], "length": 8.0}
            with patch("mt_agent.export.analyse", return_value=b):
                outs = export_clips(plan, d, d / "o", look=look)
            self.assertEqual(len(outs), 2)
            for o in outs:
                self.assertAlmostEqual(duration(str(o)), 3.0, delta=0.2)  # sans calage : 3,4 s

if __name__ == "__main__": unittest.main()
