import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None
from mt_agent.approval import save_plan
from mt_agent.ffx import run_ffmpeg
from mt_agent.models import Plan, Scene, Source

APP = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"

def _btn(at, label: str):
    return next(b for b in at.button if b.label == label)

def _metric(at, label: str) -> str:
    return next(m.value for m in at.metric if m.label == label)

def _cases(at) -> list:
    return [c for c in at.checkbox if str(c.key).startswith("sel:")]

@unittest.skipIf(AppTest is None, "streamlit absent")
class Dashboard(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory(); self.addCleanup(t.cleanup)
        self.r = Path(t.name); (self.r / "inbox").mkdir()
        c = lambda col, d: ["-f", "lavfi", "-i", f"color=c={col}:s=320x240:d={d}:r=25"]
        run_ffmpeg([*c("red", 3), *c("blue", 3), *c("green", 4), "-filter_complex",
                    "[0][1][2]concat=n=3:v=1:a=0", "-pix_fmt", "yuv420p"], self.r / "inbox" / "s.mp4")
        plan = Plan(sources=[Source(id="a", path="inbox/s.mp4", duration=10.0)],
                    scenes=[Scene(source_id="a", start=0, end=3), Scene(source_id="a", start=3, end=6),
                            Scene(source_id="a", start=6, end=10)])
        d = self.r / "workspace" / "plans"; d.mkdir(parents=True)
        save_plan(plan, d)
        self.out = self.r / "output"
        self.enterContext(patch("mt_agent.paths.ROOT", self.r))

    def test_flow(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(_metric(at, "Statut"), "À valider")
        self.assertEqual(_metric(at, "Scènes"), "0/3")
        self.assertTrue(_btn(at, "Exporter la vidéo assemblée").disabled)
        self.assertTrue(_btn(at, "Approuver").disabled)
        at.text_input(key="spec").set_value("1-2").run()
        _btn(at, "Appliquer la sélection").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(_metric(at, "Scènes"), "2/3")
        _btn(at, "Approuver").click().run()
        self.assertEqual(_metric(at, "Statut"), "Approuvé")
        self.assertFalse(_btn(at, "Exporter la vidéo assemblée").disabled)
        self.assertEqual(list(self.out.glob("*.mp4")), [])      # approuver n'exporte jamais
        _btn(at, "Exporter la vidéo assemblée").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(list(self.out.glob("*.mp4"))), 1)

    def test_cases(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertEqual(len(_cases(at)), 3)
        _cases(at)[0].check().run()
        _cases(at)[2].check().run()
        _btn(at, "Appliquer la sélection").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(_metric(at, "Scènes"), "2/3")
        self.assertEqual([c.value for c in _cases(at)], [True, False, True])
        _btn(at, "Tout cocher").click().run()
        self.assertEqual([c.value for c in _cases(at)], [True, True, True])
        _btn(at, "Tout décocher").click().run()
        self.assertEqual([c.value for c in _cases(at)], [False, False, False])

    def test_decouper(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self.assertEqual(len(at.exception), 0)
        _btn(at, "Découper").click().run()
        self.assertEqual(len(at.exception), 0)
        maxes = [Plan.model_validate_json(f.read_text()).options.max_scene_seconds
                 for f in (self.r / "workspace" / "plans").iterdir()]
        self.assertIn(5.0, maxes)

    def test_clips(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self.assertTrue(_btn(at, "Exporter en clips séparés").disabled)
        at.text_input(key="spec").set_value("1-2").run()
        _btn(at, "Appliquer la sélection").click().run()
        _btn(at, "Approuver").click().run()
        self.assertFalse(_btn(at, "Exporter en clips séparés").disabled)
        _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(sorted(f.name for f in self.out.glob("clips/*/*.mp4")), ["001.mp4", "002.mp4"])
        self.assertEqual(list(self.out.glob("*.mp4")), [])
        self.assertFalse(_btn(at, "Exporter la vidéo assemblée").disabled)

    def test_decouper_en_lot(self) -> None:
        (self.r / "inbox" / "t.mp4").write_bytes((self.r / "inbox" / "s.mp4").read_bytes())
        at = AppTest.from_file(str(APP), default_timeout=180).run()
        self.assertEqual(len(at.exception), 0)
        _btn(at, "Découper les 2 vidéos").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        names = {Path(Plan.model_validate_json(f.read_text()).sources[0].path).name
                 for f in (self.r / "workspace" / "plans").iterdir()}
        self.assertTrue({"s.mp4", "t.mp4"} <= names)

    def test_fenetres(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        _btn(at, "Fenêtre 3–4 s").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual((at.number_input(key="scan_lo").value, at.number_input(key="scan_hi").value), (3.0, 4.0))
        _btn(at, "Découper").click().run()
        self.assertEqual(len(at.exception), 0)
        maxes = [Plan.model_validate_json(f.read_text()).options.max_scene_seconds
                 for f in (self.r / "workspace" / "plans").iterdir()]
        self.assertIn(4.0, maxes)
        _btn(at, "Fenêtre 3–5 s").click().run()
        self.assertEqual(at.number_input(key="scan_hi").value, 5.0)

    def test_rendu_choisi(self) -> None:
        from mt_agent.export import Look, export_clips
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        at.text_input(key="spec").set_value("1-2").run()
        _btn(at, "Appliquer la sélection").click().run()
        _btn(at, "Approuver").click().run()
        at.radio(key="look_fit").set_value("Plein cadre (recadré)").run()
        at.slider(key="look_pos").set_value(0).run()
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(fit="fill", background="blur", anchor=0.0))
        self.assertEqual(len(list(self.out.glob("clips/*/*.mp4"))), 2)

    def test_rendu_aucun(self) -> None:
        from mt_agent.export import Look, export_clips
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        at.text_input(key="spec").set_value("1-2").run()
        _btn(at, "Appliquer la sélection").click().run()
        _btn(at, "Approuver").click().run()
        at.radio(key="look_fit").set_value("Aucun (source telle quelle)").run()
        self.assertEqual([r.key for r in at.radio if r.key in ("look_bg", "look_pos")], [])
        self.assertEqual([x.key for x in at.slider if x.key == "look_pos"], [])
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(fit="none", background="blur", anchor=0.5))
        self.assertEqual(len(list(self.out.glob("clips/*/*.mp4"))), 2)
        _btn(at, "Exporter la vidéo assemblée").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(len(list(self.out.glob("*.mp4"))), 1)

    def _ready(self, at) -> None:
        at.text_input(key="spec").set_value("1-2").run()
        _btn(at, "Appliquer la sélection").click().run()
        _btn(at, "Approuver").click().run()

    def _keys(self, at, kind: str, pre: str) -> list[str]:
        return [str(x.key) for x in getattr(at, kind) if str(x.key).startswith(pre)]

    def _ff(self, *args: str) -> None:
        import subprocess
        subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)

    def _tone(self) -> None:
        (self.r / "music").mkdir(exist_ok=True)
        self._ff("-f", "lavfi", "-i", "sine=frequency=220:duration=2", str(self.r / "music" / "m.wav"))

    def _with_audio(self) -> None:
        p = self.r / "inbox" / "s.mp4"
        p.unlink()
        self._ff("-f", "lavfi", "-i", "color=c=red:s=320x240:d=10:r=25", "-f", "lavfi",
                 "-i", "sine=frequency=440:duration=10", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(p))

    def test_son_source_muette(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(at.radio(key="snd_mode").options, ["Sans audio", "Musique ajoutée"])
        for kind in ("slider", "selectbox", "checkbox", "number_input"):
            self.assertEqual(self._keys(at, kind, "snd_"), [], kind)
        at.radio(key="snd_mode").set_value("Musique ajoutée").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(sorted(self._keys(at, "checkbox", "snd_")), ["snd_echo", "snd_snap", "snd_snapc"])  # pas de mix : source muette ; calage décoché en option
        self.assertEqual(sorted(self._keys(at, "slider", "snd_")), ["snd_fade", "snd_mdb"])
        self.assertEqual(self._keys(at, "selectbox", "snd_"), [])  # music/ absent ou vide

    def test_son_musique_echo_export(self) -> None:
        from mt_agent.export import Look, export_clips
        from mt_agent.ffx import has_audio
        self._tone()
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self._ready(at)
        at.radio(key="snd_mode").set_value("Musique ajoutée").run()
        self.assertEqual(at.selectbox(key="snd_file").options, ["m.wav"])
        self.assertEqual(self._keys(at, "slider", "snd_e"), [])  # écho masqué tant que décoché
        at.checkbox(key="snd_echo").check().run()
        self.assertEqual(sorted(self._keys(at, "slider", "snd_e")), ["snd_edec", "snd_ems"])
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(
            fit="bars", background="blur", anchor=0.5, audio="music", music="music/m.wav",
            echo=True, echo_ms=120.0, echo_decay=0.3))
        files = sorted(self.out.glob("clips/*/*.mp4"))
        self.assertEqual(len(files), 2)
        self.assertTrue(all(has_audio(str(f)) for f in files))

    def test_son_source_audio(self) -> None:
        from mt_agent.export import Look, export_clips
        from mt_agent.ffx import has_audio
        self._with_audio()
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self._ready(at)
        self.assertEqual(at.radio(key="snd_mode").options, ["Sans audio", "Audio de la source", "Musique ajoutée"])
        self.assertEqual(self._keys(at, "slider", "snd_"), [])
        at.radio(key="snd_mode").set_value("Audio de la source").run()
        self.assertEqual(self._keys(at, "slider", "snd_"), ["snd_src_db"])
        self.assertEqual(self._keys(at, "checkbox", "snd_"), ["snd_echo"])  # pas de mix hors musique
        at.radio(key="snd_mode").set_value("Musique ajoutée").run()
        self.assertEqual(sorted(self._keys(at, "checkbox", "snd_")), ["snd_echo", "snd_mix", "snd_snap", "snd_snapc"])
        at.radio(key="snd_mode").set_value("Audio de la source").run()
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(
            fit="bars", background="blur", anchor=0.5, audio="source", audio_db=0.0))
        files = sorted(self.out.glob("clips/*/*.mp4"))
        self.assertEqual(len(files), 2)
        self.assertTrue(all(has_audio(str(f)) for f in files))

    def test_format_miroir(self) -> None:
        from mt_agent.export import Look, export_clips
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self._ready(at)
        self.assertEqual(at.radio(key="look_ratio").options, ["Suivre le plan", "9:16", "16:9", "1:1"])
        at.radio(key="look_ratio").set_value("16:9").run()
        _btn(at, "Miroir : toutes").click().run()
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(
            fit="bars", background="blur", anchor=0.5, ratio="16:9", mirror_only=frozenset({1, 2, 3})))
        self.assertEqual(len(list(self.out.glob("clips/*/*.mp4"))), 2)

    def _mirs(self, at) -> list:
        return [c for c in at.checkbox if str(c.key).startswith("mir:")]

    def test_miroir_par_scenes(self) -> None:
        from mt_agent.export import Look, export_clips
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self._ready(at)
        self.assertEqual([c.value for c in self._mirs(at)], [False, False, False])
        self._mirs(at)[1].check().run()
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(
            fit="bars", background="blur", anchor=0.5, mirror_only=frozenset({2})))
        self.assertEqual(len(list(self.out.glob("clips/*/*.mp4"))), 2)

    def test_miroir_toutes_aucune(self) -> None:
        from mt_agent.export import Look, export_clips
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        self._ready(at)
        _btn(at, "Miroir : toutes").click().run()
        self.assertEqual([c.value for c in self._mirs(at)], [True, True, True])
        with patch("mt_agent.export.export_clips", wraps=export_clips) as m:
            _btn(at, "Exporter en clips séparés").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(m.call_args.kwargs["look"], Look(
            fit="bars", background="blur", anchor=0.5, mirror_only=frozenset({1, 2, 3})))
        _btn(at, "Miroir : aucune").click().run()
        self.assertEqual([c.value for c in self._mirs(at)], [False, False, False])

    def test_miroir_independant_de_garder(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        self._mirs(at)[2].check().run()
        for label in ("Tout cocher", "Tout décocher", "Inverser"):
            _btn(at, label).click().run()
            self.assertEqual([c.value for c in self._mirs(at)], [False, False, True], label)

    def test_aucun_masque_format(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=60).run()
        at.radio(key="look_fit").set_value("Aucun (source telle quelle)").run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual([r.key for r in at.radio if r.key == "look_ratio"], [])
        self.assertEqual(self._keys(at, "checkbox", "look_"), [])

    def _scenes(self) -> list[list[tuple[float, float]]]:
        return [[(x.start, x.end) for x in Plan.model_validate_json(f.read_text()).scenes]
                for f in (self.r / "workspace" / "plans").iterdir()]

    def test_mode_manuel(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        at.radio(key="scan_mode").set_value("Manuel (plages)").run()
        self.assertEqual(len(at.number_input), 0)  # Min/Max masqués hors Auto
        at.text_area(key="scan_spans").set_value("4-9;1-2.5").run()
        _btn(at, "Créer le plan").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        self.assertIn([(4.0, 9.0), (1.0, 2.5)], self._scenes())

    def test_mode_manuel_invalide(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        at.radio(key="scan_mode").set_value("Manuel (plages)").run()
        at.text_area(key="scan_spans").set_value("9-4").run()
        _btn(at, "Créer le plan").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(self._scenes()), 1)  # aucun plan ajouté

    def test_mode_aucune(self) -> None:
        at = AppTest.from_file(str(APP), default_timeout=120).run()
        at.radio(key="scan_mode").set_value("Aucune (vidéo entière)").run()
        _btn(at, "Garder la vidéo entière").click().run()
        self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(at.error), 0)
        whole = [sc for sc in self._scenes() if len(sc) == 1]
        self.assertEqual(len(whole), 1)
        self.assertEqual(whole[0][0][0], 0.0)
        self.assertAlmostEqual(whole[0][0][1], 10.0, delta=0.2)
