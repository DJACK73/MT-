import subprocess
import tempfile
import unittest
from pathlib import Path

from mt_agent.approval import PlanError, approve
from mt_agent.export import Look, _look, _size, build_graph, export_clips
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Options, Plan, Scene, Source


def _plan(profile: str = "vertical") -> Plan:
    return Plan(options=Options(profile=profile),
                sources=[Source(id="s", path="inbox/src.mp4", duration=6.0)],
                scenes=[Scene(source_id="s", start=0.0, end=1.5, selected=True)])


def _dims(clip: Path) -> str:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height", "-of", "csv=p=0", str(clip)],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


class RatioTest(unittest.TestCase):
    def test_tailles(self) -> None:
        self.assertEqual(_size(_plan(), Look(ratio="9:16")), (1080, 1920))
        self.assertEqual(_size(_plan(), Look(ratio="16:9")), (1920, 1080))
        self.assertEqual(_size(_plan(), Look(ratio="1:1")), (1080, 1080))

    def test_defaut_suit_le_profil(self) -> None:
        self.assertEqual(_size(_plan("vertical"), None), (1080, 1920))
        self.assertEqual(_size(_plan("youtube"), Look()), (1920, 1080))

    def test_format_inconnu(self) -> None:
        with self.assertRaises(PlanError):
            _size(_plan(), Look(ratio="4:3"))

    def test_refus_avec_aucun(self) -> None:
        with self.assertRaises(PlanError):
            _look(_plan(), Look(fit="none", ratio="1:1"))

    def test_graph_carre(self) -> None:
        _, fc = build_graph(_plan(), Look(fit="bars", background="black", ratio="1:1"))
        self.assertIn("scale=1080:1080:force_original_aspect_ratio=decrease,pad=1080:1080", fc)

    def test_clips_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "inbox" / "src.mp4"
            src.parent.mkdir(parents=True)
            run_ffmpeg(["-f", "lavfi", "-i", "testsrc=size=320x240:rate=25", "-t", "2",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p"], src)
            plan = approve(_plan())
            for fit in ("bars", "fill"):
                for ratio, wh in (("9:16", "1080,1920"), ("16:9", "1920,1080"), ("1:1", "1080,1080")):
                    with self.subTest(fit=fit, ratio=ratio):
                        clip = export_clips(plan, root, root / "output",
                                            look=Look(fit=fit, background="black", ratio=ratio))[0]
                        self.assertEqual(_dims(clip), wh)


if __name__ == "__main__":
    unittest.main()
