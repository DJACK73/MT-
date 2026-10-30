import unittest

from mt_agent.export import FX, Look
from mt_agent.grade import FX_UI, fx_cost, grade_kw


class GradeUiTest(unittest.TestCase):
    def test_defaults_omitted(self) -> None:
        self.assertEqual(grade_kw(0, 100, 100, []), {})

    def test_bounds_exact(self) -> None:
        lo, hi = grade_kw(-30, 50, 0, []), grade_kw(30, 150, 200, [])
        self.assertEqual((lo["bright"], lo["contrast"], lo["sat"]), (-0.3, 0.5, 0.0))
        self.assertEqual((hi["bright"], hi["contrast"], hi["sat"]), (0.3, 1.5, 2.0))
        for kw in (lo, hi):
            Look(**kw)

    def test_fx_active(self) -> None:
        look = Look(**grade_kw(0, 100, 100, ["grain", "bw"]))
        self.assertEqual(look.fx, frozenset({"grain", "bw"}))

    def test_names_match_core(self) -> None:
        self.assertEqual(set(FX_UI), set(FX))

    def test_cost(self) -> None:
        self.assertEqual(fx_cost({}), 1.0)
        self.assertEqual(fx_cost({"fx": frozenset({"bw"})}), 1.0)
        self.assertEqual(fx_cost({"fx": frozenset(FX)}), 3.0)


if __name__ == "__main__":
    unittest.main()
