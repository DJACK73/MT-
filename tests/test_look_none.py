import unittest
from types import SimpleNamespace as NS

from mt_agent.approval import PlanError
from mt_agent.export import Look, _look, _node, build_graph


def _plan(sources: list[str], framing: str = "blur_pad") -> NS:
    return NS(
        options=NS(framing=framing, profile="vertical"),
        sources=[NS(id=s, path=f"{s}.mp4") for s in sources],
        scenes=[NS(selected=True, source_id=s, start=0.0, end=3.0, path=None) for s in sources],
    )


class LookNone(unittest.TestCase):
    def test_node_trim_seul(self) -> None:
        n = _node(0, 0, 1.0, 4.0, "none", 1080, 1920)
        self.assertTrue(n.startswith("[0:v]trim=start=1.000:end=4.000"))
        for banned in ("scale", "pad", "boxblur", "crop", "fps", "overlay"):
            self.assertNotIn(banned, n)
        self.assertTrue(n.endswith("[v0]"))

    def test_look_none(self) -> None:
        self.assertEqual(_look(_plan(["a"]), Look(fit="none"))[0], "none")

    def test_fit_none_python_inchange(self) -> None:
        self.assertEqual(_look(_plan(["a"], "blur_pad"), None)[0], "blur_pad")
        self.assertEqual(_look(_plan(["a"], "crop_center"), None)[0], "crop_center")

    def test_graph_une_source(self) -> None:
        _, fc = build_graph(_plan(["a"]), Look(fit="none"))
        self.assertNotIn("scale", fc)

    def test_graph_deux_sources_refuse(self) -> None:
        with self.assertRaises(PlanError):
            build_graph(_plan(["a", "b"]), Look(fit="none"))


if __name__ == "__main__":
    unittest.main()
