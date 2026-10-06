import os, tempfile, unittest
from pathlib import Path
from mt_agent.clean import plan_clean, run_clean

def _mk(root: Path) -> None:
    for rel in ("workspace/plans/a.json", "workspace/thumbs/k/001.jpg", "workspace/previews/p.mp4",
                "workspace/archive-x/old.json", "output/o.mp4", "inbox/v.mp4", "inbox/.gitkeep"):
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")

def _names(root: Path, rel: str) -> set[str]:
    return {p.name for p in (root / rel).iterdir()}

class CleanTest(unittest.TestCase):
    def setUp(self) -> None:
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        _mk(self.root)

    def test_niveau1(self) -> None:
        self.assertEqual({p.name for p in plan_clean(self.root, 1)}, {"a.json", "k", "p.mp4"})
        self.assertEqual(run_clean(self.root, 1), (3, []))
        self.assertEqual(_names(self.root, "workspace/plans"), set())
        self.assertEqual(_names(self.root, "workspace/thumbs"), set())
        self.assertEqual(_names(self.root, "output"), {"o.mp4"})
        self.assertEqual(_names(self.root, "inbox"), {"v.mp4", ".gitkeep"})
        self.assertTrue((self.root / "workspace/archive-x/old.json").exists())

    def test_niveau2(self) -> None:
        self.assertEqual(run_clean(self.root, 2), (4, []))
        self.assertEqual(_names(self.root, "output"), set())
        self.assertEqual(_names(self.root, "inbox"), {"v.mp4", ".gitkeep"})

    def test_niveau3(self) -> None:
        self.assertEqual(run_clean(self.root, 3), (5, []))
        self.assertEqual(_names(self.root, "inbox"), {".gitkeep"})
        self.assertTrue((self.root / "output").is_dir())
        self.assertTrue((self.root / "workspace/archive-x/old.json").exists())

    def test_lien_non_suivi(self) -> None:
        with tempfile.TemporaryDirectory() as ext:
            target = Path(ext) / "precieux.txt"
            target.write_text("x")
            (self.root / "output" / "lien").symlink_to(target)
            run_clean(self.root, 2)
            self.assertTrue(target.exists())
            self.assertEqual(_names(self.root, "output"), set())

    def test_niveau_inconnu_et_dossiers_absents(self) -> None:
        with self.assertRaises(ValueError):
            plan_clean(self.root, 4)
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run_clean(Path(t), 3), (0, []))

    @unittest.skipIf(os.geteuid() == 0, "root ignore les droits")
    def test_inbox_lecture_seule_ne_supprime_rien(self) -> None:
        os.chmod(self.root / "inbox", 0o555)
        self.addCleanup(os.chmod, self.root / "inbox", 0o755)
        with self.assertRaises(PermissionError):
            run_clean(self.root, 3)
        self.assertEqual(_names(self.root, "output"), {"o.mp4"})
        self.assertEqual(_names(self.root, "workspace/plans"), {"a.json"})
