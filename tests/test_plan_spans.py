import unittest
from mt_agent.cmd import plan_spans

CUTS, TOTAL = [3.0, 4.0, 12.0], 14.0

class PlanSpansTest(unittest.TestCase):
    def test_sans_max_fusion_historique(self) -> None:
        self.assertEqual(plan_spans(CUTS, TOTAL, 3.0, None), [(0.0, 4.0), (4.0, 14.0)])

    def test_avec_max_fenetre_3_5(self) -> None:
        self.assertEqual(plan_spans(CUTS, TOTAL, 3.0, 5.0), [(0.0, 4.0), (4.0, 9.0), (9.0, 14.0)])

    def test_max_inferieur_au_min_refuse(self) -> None:
        with self.assertRaises(ValueError):
            plan_spans(CUTS, TOTAL, 5.0, 3.0)

if __name__ == "__main__":
    unittest.main()
