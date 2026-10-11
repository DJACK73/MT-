import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.approval import PlanError, approve
from mt_agent.export import Look, _music, build_graph, export_clips, export_plan
from mt_agent.ffx import duration, run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

SPANS = [(0.0, 1.5), (1.5, 3.0), (3.0, 4.5)]


def _astream(path: Path) -> dict | None:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
                        "-show_entries", "stream=codec_name,channels,duration",
                        "-of", "json", str(path)], capture_output=True, text=True, check=True)
    streams = json.loads(r.stdout)["streams"]
    return streams[0] if streams else None


def _plan(root: Path) -> Plan:
    src = root / "inbox" / "src.mp4"
    src.parent.mkdir(parents=True)
    run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=320x240:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "6",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac"], src)
    return Plan(options=Options(framing="crop_center"),
                sources=[Source(id="s", path="inbox/src.mp4", duration=6.0)],
                scenes=[Scene(source_id="s", start=a, end=b, selected=True) for a, b in SPANS])


def _music_file(root: Path, dur: float) -> str:
    m = root / "music" / "m.wav"
    m.parent.mkdir(exist_ok=True)
    run_ffmpeg(["-f", "lavfi", "-i", f"sine=frequency=220:duration={dur}"], m, fmt="wav")
    return "music/m.wav"


class MusicTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.plan = approve(_plan(self.root))
        self.out = self.root / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_graph_musique(self) -> None:
        srcs, fc = build_graph(self.plan, Look(audio="music", music="music/m.wav"))
        self.assertEqual(srcs, ["inbox/src.mp4", "music/m.wav"])
        self.assertIn("[1:a]atrim=start=0.000:end=4.500,asetpts=PTS-STARTPTS,"
                      "aformat=sample_rates=48000:channel_layouts=stereo,"
                      "afade=t=in:d=0.3,afade=t=out:st=4.200:d=0.3[aud]", fc)
        self.assertNotIn("a=1", fc)

    def test_graph_mix(self) -> None:
        _, fc = build_graph(self.plan, Look(audio="mix", music="music/m.wav", audio_db=-3.0))
        self.assertIn("concat=n=3:v=1:a=1[out][ac]", fc)
        self.assertIn("[ac]volume=-3dB[src]", fc)
        self.assertIn("sidechaincompress", fc)
        self.assertIn("[audd][src2]amix=inputs=2:duration=first:normalize=0[aud]", fc)

    def test_refus_parametres(self) -> None:
        self.assertFalse(_music(Look())[0])
        with self.assertRaises(PlanError):
            _music(Look(audio="music"))
        with self.assertRaises(PlanError):
            _music(Look(audio="music", music="m.wav", music_fade=2.0))

    def test_clip_musique(self) -> None:
        m = _music_file(self.root, 3.0)
        for f in export_clips(self.plan, self.root, self.out, look=Look(audio="music", music=m)):
            a = _astream(f)
            self.assertEqual((a["codec_name"], a["channels"]), ("aac", 2))
            self.assertAlmostEqual(float(a["duration"]), 1.5, delta=0.15)

    def test_clip_musique_boucle(self) -> None:
        m = _music_file(self.root, 0.5)  # plus courte que le clip : bouclée
        for f in export_clips(self.plan, self.root, self.out, look=Look(audio="music", music=m)):
            self.assertAlmostEqual(float(_astream(f)["duration"]), 1.5, delta=0.15)

    def test_clip_mix(self) -> None:
        m = _music_file(self.root, 3.0)
        for f in export_clips(self.plan, self.root, self.out, look=Look(audio="mix", music=m)):
            a = _astream(f)
            self.assertEqual(a["codec_name"], "aac")
            self.assertAlmostEqual(float(a["duration"]), 1.5, delta=0.15)

    def test_debut_trop_loin(self) -> None:
        m = _music_file(self.root, 1.0)
        with self.assertRaises(PlanError):
            export_clips(self.plan, self.root, self.out, look=Look(audio="music", music=m, music_start=5.0))

    def test_assemble_musique(self) -> None:
        m = _music_file(self.root, 2.0)
        mp4, _ = export_plan(self.plan, self.root, self.out, look=Look(audio="music", music=m, fit="none"))
        self.assertAlmostEqual(duration(str(mp4)), 4.5, delta=0.2)
        self.assertEqual(_astream(mp4)["codec_name"], "aac")


if __name__ == "__main__":
    unittest.main()
