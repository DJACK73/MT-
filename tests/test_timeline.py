import unittest

from mt_agent.timeline import frise_html


class FriseHtmlTest(unittest.TestCase):
    def test_coupes_et_largeurs(self) -> None:
        h = frise_html([{"uri": "data:x", "dur": 4.0, "label": "1"}, {"uri": None, "dur": 1.0, "label": "2"}])
        self.assertEqual(h.count('class="fr-j"'), 1)
        self.assertIn("width:112px", h)
        self.assertIn("width:72px", h)
        self.assertEqual(h.count("<img"), 1)

    def test_echappement(self) -> None:
        h = frise_html([{"uri": None, "dur": 2.0, "label": "<b>x</b>"}])
        self.assertNotIn("<b>", h)
        self.assertIn("&lt;b&gt;", h)

    def test_vide_et_une_scene(self) -> None:
        self.assertNotIn('class="fr-s"', frise_html([]))
        self.assertEqual(frise_html([{"uri": None, "dur": 3.0, "label": "1"}]).count("fr-j"), 0)


if __name__ == "__main__":
    unittest.main()
