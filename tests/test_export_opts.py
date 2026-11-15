import tempfile
import unittest
from pathlib import Path

from mt_agent import webapi


class ExportOptsTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)
        (self.root / "music").mkdir()
        (self.root / "music" / "a.m4a").write_bytes(b"x")
        (self.root / "music" / "n.txt").write_bytes(b"x")

    def look(self, audio, o):
        return webapi._look(self.root, "9:16", 1.0, audio, frozenset(), o)

    def test_list_music(self):
        self.assertEqual(webapi.list_music(self.root), ["a.m4a"])

    def test_music_mix_ok(self):
        lk = self.look("mix", {"music": "a.m4a", "snap_beats": True, "echo": True})
        self.assertEqual(lk.music, "music/a.m4a")
        self.assertTrue(lk.snap_beats)
        self.assertTrue(lk.echo)

    def test_music_hors_dossier(self):
        with self.assertRaises(ValueError):
            self.look("music", {"music": "../x.m4a"})

    def test_calage_sans_musique(self):
        with self.assertRaises(ValueError):
            self.look("source", {"snap_beats": True})

    def test_echo_sans_son(self):
        with self.assertRaises(ValueError):
            self.look("none", {"echo": True})

    def test_fit_inconnu(self):
        with self.assertRaises(ValueError):
            self.look("none", {"fit": "zoom"})

    def test_fond_inconnu(self):
        with self.assertRaises(ValueError):
            self.look("none", {"background": "rouge"})

    def test_nombre_hors_bornes(self):
        with self.assertRaises(ValueError):
            self.look("music", {"music": "a.m4a", "music_db": 99})

    def test_booleen_invalide(self):
        with self.assertRaises(ValueError):
            self.look("music", {"music": "a.m4a", "snap_clips": "oui"})


if __name__ == "__main__":
    unittest.main()
