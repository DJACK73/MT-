import ast
import unittest
from pathlib import Path

from mt_agent.export import TRANS, Look, _trans

WANTED = {"none", "fade", "fadeblack", "fadewhite", "slide", "slideup", "dissolve", "pixelize", "hblur"}


class TransSetTest(unittest.TestCase):
    def test_keys_and_names(self) -> None:
        self.assertEqual(set(TRANS), WANTED)
        for k, v in TRANS.items():
            if k != "none":
                self.assertEqual(_trans(Look(trans=k), [4.0, 3.0]), (v, 0.5))

    def test_ui_matches_core(self) -> None:
        src = Path(__file__).resolve().parents[1] / "app" / "dashboard.py"
        if not src.exists():
            self.skipTest("dashboard.py absent")
        for n in ast.parse(src.read_text(encoding="utf-8")).body:
            if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "TRANS_UI":
                self.assertEqual(set(ast.literal_eval(n.value).values()), WANTED)
                return
        self.fail("TRANS_UI introuvable")

    def test_literal_matches_core(self) -> None:
        import typing
        hint = typing.get_type_hints(Look)["trans"]
        self.assertEqual(set(typing.get_args(hint)), set(TRANS))


if __name__ == "__main__":
    unittest.main()
