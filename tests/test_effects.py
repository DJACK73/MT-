import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.approval import PlanError, approve
from mt_agent.export import Look, _echo, _node, build_graph, export_clips
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source

W, H = 320, 240


def _plan_virtuel() -> Plan:
    return Plan(options=Options(framing="crop_center"),
                sources=[Source(id="s", path="inbox/src.mp4", duration=6.0)],
                scenes=[Scene(source_id="s", start=0.0, end=1.5, selected=True)])


def _plan_reel(root: Path) -> Plan:
    src = root / "inbox" / "src.mp4"
    src.parent.mkdir(parents=True)
    run_ffmpeg(["-f", "lavfi", "-i",
                f"color=c=black:s={W}x{H}:r=25,drawbox=x=0:y=0:w={W // 2}:h={H}:color=white:t=fill",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100", "-t", "3",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac"], src)
    return approve(Plan(options=Options(framing="crop_center"),
                        sources=[Source(id="s", path="inbox/src.mp4", duration=3.0)],
                        scenes=[Scene(source_id="s", start=0.0, end=1.5, selected=True)]))


def _bords(clip: Path) -> tuple[int, int]:
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(clip), "-frames:v", "1",
                        "-vf", "format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True)
    assert len(r.stdout) == W * H, len(r.stdout)
    return r.stdout[0], r.stdout[W - 1]  # pixel haut-gauche, pixel haut-droit


def _audio(clip: Path) -> dict:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                        "stream=codec_name,duration", "-of", "json", str(clip)],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)["streams"][0]


class EffetsTest(unittest.TestCase):
    def test_noeud_miroir(self) -> None:
        self.assertEqual(_node(0, 0, 0.0, 1.0, "none", 1080, 1920, mirror=True),
                         "[0:v]trim=start=0.000:end=1.000,setpts=PTS-STARTPTS,hflip,format=yuv420p[v0]")

    def test_noeud_sans_miroir(self) -> None:
        self.assertEqual(_node(0, 0, 0.0, 1.0, "none", 1080, 1920),
                         "[0:v]trim=start=0.000:end=1.000,setpts=PTS-STARTPTS,format=yuv420p[v0]")

    def test_echo_filtre(self) -> None:
        self.assertEqual(_echo(Look(audio="source", echo=True)), "aecho=0.8:0.9:120:0.3")

    def test_echo_inactif(self) -> None:
        self.assertEqual(_echo(None), "")
        self.assertEqual(_echo(Look(audio="source")), "")

    def test_echo_sans_audio(self) -> None:
        with self.assertRaises(PlanError):
            _echo(Look(echo=True))

    def test_echo_bornes(self) -> None:
        with self.assertRaises(PlanError):
            _echo(Look(audio="source", echo=True, echo_ms=5000.0))
        with self.assertRaises(PlanError):
            _echo(Look(audio="source", echo=True, echo_decay=0.9))

    def test_graph_echo(self) -> None:
        _, fc = build_graph(_plan_virtuel(), Look(audio="source", echo=True))
        self.assertIn("[ac]anull[aud0];[aud0]aecho=0.8:0.9:120:0.3[aud]", fc)

    def test_clip_miroir_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = _plan_reel(root)
            normal = export_clips(plan, root, root / "output", look=Look(fit="none"))[0]
            miroir = export_clips(plan, root, root / "output", look=Look(fit="none", mirror=True))[0]
            g, dr = _bords(normal)
            self.assertGreater(g, 192)  # source : blanc à gauche
            self.assertLess(dr, 64)
            g, dr = _bords(miroir)
            self.assertLess(g, 64)  # miroir : noir à gauche
            self.assertGreater(dr, 192)

    def test_clip_echo(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            plan = _plan_reel(root)
            clip = export_clips(plan, root, root / "output",
                                look=Look(fit="none", audio="source", echo=True))[0]
            a = _audio(clip)
            self.assertEqual(a["codec_name"], "aac")
            self.assertAlmostEqual(float(a["duration"]), 1.5, delta=0.15)


if __name__ == "__main__":
    unittest.main()
