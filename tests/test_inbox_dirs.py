import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mt_agent import webapi


class InboxDirsTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.root = Path(d.name)

    def put(self, rel, data=b"x"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def test_inbox_ancien_plat(self):
        self.put("inbox/a.mp4")
        self.assertEqual(webapi.list_inbox(self.root), ["a.mp4"])

    def test_inbox_sous_dossier_videos(self):
        self.put("inbox/videos/a.mp4")
        self.put("inbox/b.mp4")
        self.assertEqual(webapi.list_inbox(self.root), ["a.mp4"])

    def test_musique_sous_dossier(self):
        self.put("inbox/musique/a.m4a")
        self.put("inbox/musique/b.mp4")
        self.put("inbox/musique/c.txt")
        self.assertEqual(webapi.list_music(self.root), ["a.m4a", "b.mp4"])

    def test_musique_ancien_dossier(self):
        self.put("music/a.m4a")
        self.assertEqual(webapi.list_music(self.root), ["a.m4a"])

    def test_fichier_audio(self):
        self.put("inbox/musique/a.m4a")
        self.assertEqual(webapi._music_file(self.root, "a.m4a"), "inbox/musique/a.m4a")

    def test_video_extraite_une_fois(self):
        self.put("inbox/musique/b.mp4")

        def fake(s, o):
            Path(o).write_bytes(b"a")

        with mock.patch.object(webapi, "extract_audio", side_effect=fake) as m:
            r1 = webapi._music_file(self.root, "b.mp4")
            r2 = webapi._music_file(self.root, "b.mp4")
        self.assertEqual(r1, r2)
        self.assertEqual(r1, "workspace/previews/musique/b-1.m4a")
        self.assertEqual(m.call_count, 1)


if __name__ == "__main__":
    unittest.main()
